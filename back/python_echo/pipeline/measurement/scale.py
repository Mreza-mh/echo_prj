from __future__ import annotations

import math
import os
from typing import Literal

import cv2
import numpy as np

ScaleSource = Literal["ruler_estimate", "default", "manual"]

"""
Physical distance helpers: pixel geometry and scale (pixels per centimetre).

Linear measurements from segmentation endpoints are converted to centimetres with:

    length_cm = euclidean_pixel_distance(x1, y1, x2, y2) / pixels_per_cm

Scale is estimated from the same B-mode crop that feeds the measurement model (ruler
strip heuristic). When estimation fails, callers should pass a sensible default.
"""

"""
الگوریتم خط‌کش:
  - ناحیه سمت راست تصویر (۲۵٪ عرض) بررسی می‌شود.
  - ستونی که بیشترین پیکسل سفید را دارد به عنوان خط‌کش انتخاب می‌شود.
  - خطوط کوچک (tick) شناسایی می‌شوند.
  - فرض می‌شود فاصله هر دو تیک ۵ سانتی‌متر است.
  - بنابراین: pixels_per_cm = median(diff(tick_positions)) / 5
"""

# ==========================================
# بخش اول: توابع هندسی و تبدیل مقیاس
# ==========================================

def euclidean_pixel_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    محاسبه فاصله اقلیدسی بین دو نقطه در فضای پیکسل.
    
    ورودی:
        x1, y1: مختصات نقطه اول
        x2, y2: مختصات نقطه دوم
    
    خروجی:
        float: فاصله به پیکسل
        مثلاً euclidean_pixel_distance(158, 266, 299, 268) = 141.014...
    """
    return float(math.hypot(x2 - x1, y2 - y1))


def pixel_length_to_cm(pixel_length: float, pixels_per_cm: float) -> float:
    """
    تبدیل طول از پیکسل به سانتی‌متر.
    
    ورودی:
        pixel_length : طول به پیکسل (مثلاً 141.014)
        pixels_per_cm: مقیاس (مثلاً 28.6)
    
    خروجی:
        float: طول به سانتی‌متر
        141.014 / 28.6 = 4.93 cm
    
    خطا:
        ValueError اگر pixels_per_cm <= 0
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")
    return float(pixel_length) / float(pixels_per_cm)


def pixel_area_to_cm2(pixel_area: float, pixels_per_cm: float) -> float:
    """
    تبدیل مساحت از پیکسل مربع به سانتی‌متر مربع.
    
    ورودی:
        pixel_area   : مساحت به پیکسل مربع (مثلاً 9054)
        pixels_per_cm: مقیاس (مثلاً 28.6)
    
    خروجی:
        float: مساحت به cm²
        9054 / (28.6²) = 11.066...
    
    خطا:
        ValueError اگر pixels_per_cm <= 0
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")
    return float(pixel_area) / (float(pixels_per_cm) ** 2)


def map_model_point_to_segment(
    x: float,
    y: float,
    *,
    segment_width: int,
    segment_height: int,
    model_width: int = 640,
    model_height: int = 480,
) -> tuple[float, float]:
    """
    نگاشت مختصات از فضای مدل (640x480) به فضای تصویر واقعی (segment).
    
    ورودی:
        x, y          : مختصات در فضای مدل (مثلاً 299, 268)
        segment_width : عرض تصویر واقعی (مثلاً 612)
        segment_height: ارتفاع تصویر واقعی (مثلاً 507)
        model_width   : عرض ورودی مدل (پیش‌فرض 640)
        model_height  : ارتفاع ورودی مدل (پیش‌فرض 480)
    
    خروجی:
        (xs, ys): مختصات نگاشت‌یافته
        xs = 299 * (612/640) = 285.9
        ys = 268 * (507/480) = 283.1
    
    خطا:
        ValueError اگر segment_width یا segment_height <= 0
    """
    if segment_width <= 0 or segment_height <= 0:
        raise ValueError("segment dimensions must be positive.")
    xs = x * (segment_width / model_width)
    ys = y * (segment_height / model_height)
    return xs, ys


def length_cm_from_model_line(
    x1: float, y1: float,
    x2: float, y2: float,
    *,
    pixels_per_cm: float,
    segment_width: int,
    segment_height: int,
    model_width: int = 640,
    model_height: int = 480,
) -> float:
    """
    محاسبه طول یک خط (cm) با مختصات فضای مدل و نگاشت به فضای واقعی.
    
    ورودی:
        x1, y1, x2, y2: مختصات دو نقطه در فضای مدل (خروجی segmentation)
        pixels_per_cm  : مقیاس تصویر
        segment_width, segment_height: ابعاد تصویر واقعی
    
    خروجی:
        float: طول به سانتی‌متر
    """
    # نگاشت به فضای واقعی
    sx1, sy1 = map_model_point_to_segment(
        x1, y1,
        segment_width=segment_width, segment_height=segment_height,
        model_width=model_width, model_height=model_height
    )
    sx2, sy2 = map_model_point_to_segment(
        x2, y2,
        segment_width=segment_width, segment_height=segment_height,
        model_width=model_width, model_height=model_height
    )
    # فاصله اقلیدسی در فضای واقعی
    segment_px = euclidean_pixel_distance(sx1, sy1, sx2, sy2)
    # تبدیل به سانتی‌متر
    return pixel_length_to_cm(segment_px, pixels_per_cm)


# ==========================================
# بخش دوم: استخراج خط‌کش
# ==========================================

def _extract_ruler_info(image_bgr: np.ndarray, ruler_width_ratio: float = 0.25):
    """
    استخراج اطلاعات خط‌کش از تصویر B-mode.
    
    منطق:
      ۱) برش ۲۵٪ سمت راست تصویر
      ۲) تبدیل به grayscale و equalizeHist برای افزایش کنتراست
      ۳) آستانه‌گذاری (threshold > 200) برای پیدا کردن نوار سفید خط‌کش
      ۴) پیدا کردن ستون با بیشترین پیکسل سفید → موقعیت X خط‌کش
      ۵) در یک باند ۲۵ پیکسلی اطراف خط‌کش، contour های کوچک (tick) را پیدا می‌کند
      ۶) tickها را مرتب کرده و فاصله میانه را تقسیم بر ۵ می‌کند → pixels_per_cm
    
    ورودی:
        image_bgr        : تصویر BGR (اولین فریم ویدیو)
        ruler_width_ratio: نسبت عرض ناحیه خط‌کش (پیش‌فرض ۰.۲۵ = ۲۵٪)
    
    خروجی:
        tuple: (pixels_per_cm, tick_positions, x_global_ruler, x_start)
          - pixels_per_cm  : float یا None
          - tick_positions : لیست Y نقاط tick
          - x_global_ruler : موقعیت X خط‌کش در تصویر اصلی
          - x_start        : شروع ناحیه ROI
    """

    h, w = image_bgr.shape[:2]                        # مثلاً (1080, 1920)
    x_start = int(w * (1.0 - ruler_width_ratio))      # 1440 (شروع ۲۵٪ راست)
    roi = image_bgr[:, x_start:w]                      # ROI = تصویر[:, 1440:1920]

    # تبدیل به grayscale و افزایش کنتراست
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    # آستانه‌گذاری: پیکسل‌های خیلی روشن → سفید (خط‌کش)
    _, th = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # جمع پیکسل‌های سفید در هر ستون
    column_sum = np.sum(th, axis=0)                   # آرایه‌ای به طول عرض ROI
    if np.max(column_sum) == 0:
        # هیچ پیکسل سفیدی پیدا نشد → خط‌کش وجود ندارد
        return None, [], 0, x_start

    # ستونی که بیشترین پیکسل سفید را دارد → موقعیت خط‌کش در ROI
    x_ruler = int(np.argmax(column_sum))
    band = 25   # باند جستجوی tickها (۵۰ پیکسل)
    x1 = max(0, x_ruler - band)
    x2 = min(roi.shape[1], x_ruler + band)

    # برش باند اطراف خط‌کش
    ruler_roi = th[:, x1:x2]

    # پیدا کردن contourها (tickهای خط‌کش)
    contours, _ = cv2.findContours(ruler_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # فیلتر کردن tickها: عرض بین ۶ تا ۴۰ پیکسل، ارتفاع کمتر از ۶ پیکسل
    tick_positions = []
    for c in contours:
        x, y, wc, hc = cv2.boundingRect(c)
        if 6 < wc < 40 and hc < 6:
            tick_positions.append(y + hc // 2)   # مرکز tick

    tick_positions = sorted(tick_positions)
    # tick_positions = [120, 263, 406, 549, 692, ...]

    # موقعیت X خط‌کش در تصویر اصلی
    x_global_ruler = x_start + x_ruler

    if len(tick_positions) < 2:
        # حداقل دو tick لازم است
        return None, tick_positions, x_global_ruler, x_start

    # محاسبه فاصله بین tickها
    distances = np.diff(tick_positions)
    # distances = [143, 143, 143, 143, ...]

    # هر ۵ سانتی‌متر یک tick → تقسیم بر ۵
    pixels_per_cm = float(np.median(distances)) / 5.0
    # مثلاً median = 143 → pixels_per_cm = 143 / 5 = 28.6

    return pixels_per_cm, tick_positions, x_global_ruler, x_start


def estimate_pixels_per_cm_from_bgr(
    image_bgr: np.ndarray,
    *,
    default_pixels_per_cm: float,      # 12.0 (مقدار پیش‌فرض از آرگومان)
    ruler_width_ratio: float = 0.25,
) -> tuple[float, ScaleSource]:
    """
    تخمین مقیاس (pixels per cm) از تصویر B-mode.
    
    ورودی:
        image_bgr           : تصویر BGR (اولین فریم ویدیو)
        default_pixels_per_cm: مقیاس پیش‌فرض (اگر خط‌کش پیدا نشد)
        ruler_width_ratio   : نسبت عرض ناحیه خط‌کش
    
    خروجی:
        (pixels_per_cm, source)
          - pixels_per_cm: 28.60 (a4c) یا 32.60 (plax) یا 12.0 (پیش‌فرض)
          - source       : "ruler_estimate" یا "default"
    """
    if default_pixels_per_cm <= 0:
        raise ValueError("default_pixels_per_cm must be positive.")

    if image_bgr is None or image_bgr.size == 0:
        return default_pixels_per_cm, "default"     # تصویر نامعتبر

    h, w = image_bgr.shape[:2]
    if h < 64 or w < 64:
        return default_pixels_per_cm, "default"     # تصویر خیلی کوچک

    # استخراج اطلاعات خط‌کش
    pixels_per_cm, _, _, _ = _extract_ruler_info(image_bgr, ruler_width_ratio)

    # اعتبارسنجی: مقیاس باید بزرگتر از ۱ باشد (cm نمی‌تواند بیش از ۱ پیکسل باشد)
    if pixels_per_cm is None or pixels_per_cm <= 1.0:
        return default_pixels_per_cm, "default"     # خط‌کش معتبر پیدا نشد

    return float(pixels_per_cm), "ruler_estimate"
    # خروجی واقعی: (28.60, "ruler_estimate")


# ==========================================
# بخش سوم: مصورسازی (Visualization)
# ==========================================

def visualize_scale_result(
    image_bgr: np.ndarray,
    pixels_per_cm: float,              # 28.60
    source: str,                       # "ruler_estimate"
    save_path: str | os.PathLike | None = None,   # "debug_scale_output.jpg"
    show: bool = False,
    ruler_width_ratio: float = 0.25
):
    """
    رسم تصویر دیباگ برای تأیید صحت تشخیص خط‌کش.
    
    عناصر رسم‌شده:
      ۱) سایه آبی روی ناحیه خط‌کش (۲۵٪ راست)
      ۲) خط عمودی زرد روی محور خط‌کش
      ۳) نقاط قرمز روی tickهای شناسایی‌شده
      ۴) خطوط آبی بین tickها (هر ۵ سانتی‌متر)
      ۵) خطوط افقی سبز هر ۱ سانتی‌متر (grid مجازی)
      ۶) متن سفید با پس‌زمینه مشکی: "Scale: 28.60 px/cm (ruler_estimate)"
    
    ورودی:
        image_bgr    : تصویر اصلی
        pixels_per_cm: مقیاس تخمین‌زده‌شده
        source       : منبع مقیاس
        save_path    : مسیر ذخیره تصویر دیباگ
        show         : اگر True باشد، تصویر را نمایش می‌دهد
    """
    vis_img = image_bgr.copy()
    h, w = vis_img.shape[:2]

    # استخراج مجدد اطلاعات خط‌کش برای رسم
    estimated_px_cm, ticks, x_global_ruler, x_start = _extract_ruler_info(
        image_bgr, ruler_width_ratio
    )

    # 1. سایه زدن ناحیه خط‌کش (آبی تیره نیمه‌شفاف)
    overlay = vis_img.copy()
    cv2.rectangle(overlay, (x_start, 0), (w, h), (40, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, vis_img, 0.6, 0, vis_img)

    # 2. رسم محور اصلی خط‌کش (خط عمودی زرد)
    if x_global_ruler > 0:
        cv2.line(vis_img, (x_global_ruler, 0), (x_global_ruler, h), (0, 255, 255), 2)

    # 3. رسم نقاط tick شناسایی‌شده (دایره قرمز)
    points = []
    for y in ticks:
        cv2.circle(vis_img, (x_global_ruler, y), 5, (0, 0, 255), -1)
        points.append((x_global_ruler, y))

    # وصل کردن tickها با خط آبی
    for i in range(len(points) - 1):
        cv2.line(vis_img, points[i], points[i + 1], (255, 0, 0), 2)

    # 4. رسم grid یک سانتی‌متری (خطوط افقی سبز)
    if pixels_per_cm > 0 and len(ticks) > 0:
        start_y = ticks[0]
        current_y = float(start_y)

        # به سمت پایین
        while current_y < h:
            cv2.line(vis_img, (x_start, int(current_y)), (w, int(current_y)), (0, 255, 0), 1)
            current_y += pixels_per_cm

        # به سمت بالا
        current_y = float(start_y) - pixels_per_cm
        while current_y > 0:
            cv2.line(vis_img, (x_start, int(current_y)), (w, int(current_y)), (0, 255, 0), 1)
            current_y -= pixels_per_cm

    # 5. متن اطلاعات
    text = f"Scale: {pixels_per_cm:.2f} px/cm ({source})"
    # text = "Scale: 28.60 px/cm (ruler_estimate)"
    cv2.rectangle(vis_img, (10, 10), (450, 50), (0, 0, 0), -1)
    cv2.putText(vis_img, text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # ذخیره
    if save_path:
        cv2.imwrite(str(save_path), vis_img)
        print(f"Scale debug image saved to: {save_path}")

    if show:
        cv2.imshow("Scale Debug", vis_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()



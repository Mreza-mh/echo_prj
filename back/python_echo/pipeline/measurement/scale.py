"""
توابع کمکی فاصله فیزیکی: هندسه پیکسلی و مقیاس (pixels per cm).

اندازه‌گیری‌های خطی از نقاط خروجی segmentation با این فرمول به سانتی‌متر تبدیل می‌شوند:

    length_cm = euclidean_pixel_distance(x1, y1, x2, y2) / pixels_per_cm

مقیاس از همان تصویر B-mode ورودی مدل تخمین زده می‌شود (الگوریتم خط‌کش).
اگر تخمین شکست بخورد، فراخواننده باید یک مقدار پیش‌فرض معقول بدهد.

الگوریتم خط‌کش:
  - ناحیه سمت راست تصویر (۲۵٪ عرض) بررسی می‌شود.
  - ستونی که بیشترین پیکسل سفید را دارد به عنوان خط‌کش انتخاب می‌شود.
  - خطوط کوچک (tick) شناسایی می‌شوند.
  - فرض می‌شود فاصله هر دو تیک ۵ سانتی‌متر است.
  - بنابراین: pixels_per_cm = median(diff(tick_positions)) / 5
"""

from __future__ import annotations

import math
import os
from typing import Literal

import cv2
import numpy as np

# منبع مقیاس: تخمین از خط‌کش، مقدار پیش‌فرض، یا ورودی دستی کاربر
ScaleSource = Literal["ruler_estimate", "default", "manual"]


# ==============================================================================
# بخش اول: توابع هندسی و تبدیل مقیاس
# ==============================================================================

def euclidean_pixel_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    فاصله اقلیدسی بین دو نقطه در فضای پیکسل.

    مثال: euclidean_pixel_distance(158, 266, 299, 268) = 141.014...
    """
    return float(math.hypot(x2 - x1, y2 - y1))   #رادیکال فاصله ایکس ها بتوان دو بعلاوه فاصله وای ها بتوان دو


def pixel_length_to_cm(pixel_length: float, pixels_per_cm: float) -> float:
    """
    تبدیل طول از پیکسل به سانتی‌متر.

    مثال: 141.014 پیکسل با مقیاس 28.6 → 4.93 cm

    خطا:
        ValueError اگر pixels_per_cm <= 0
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")
    return float(pixel_length) / float(pixels_per_cm)


def pixel_area_to_cm2(pixel_area: float, pixels_per_cm: float) -> float:
    """
    تبدیل مساحت از پیکسل مربع به سانتی‌متر مربع.

    مثال: 9054 پیکسل مربع با مقیاس 28.6 → 9054 / 28.6² = 11.07 cm²

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

    مدل روی تصویر resize شده کار می‌کند؛ برای اندازه‌گیری درست باید مختصات
    به ابعاد واقعی تصویر برگردند (مقیاس‌دهی خطی در هر محور).

    مثال:
        (299, 268) در فضای 640x480 با segment ابعاد 612x507:
        xs = 299 * (612/640) = 285.9
        ys = 268 * (507/480) = 283.1

    خطا:
        ValueError اگر ابعاد segment مثبت نباشند
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
    محاسبه طول یک خط (cm) از مختصات فضای مدل.

    مراحل:
      ۱) نگاشت هر دو نقطه به فضای تصویر واقعی
      ۲) فاصله اقلیدسی در فضای واقعی
      ۳) تقسیم بر pixels_per_cm → سانتی‌متر

    ورودی:
        x1, y1, x2, y2: مختصات دو نقطه در فضای مدل (خروجی segmentation)
        pixels_per_cm : مقیاس تصویر
        segment_width, segment_height: ابعاد تصویر واقعی
    """
    sx1, sy1 = map_model_point_to_segment(
        x1, y1,
        segment_width=segment_width, segment_height=segment_height,
        model_width=model_width, model_height=model_height,
    )
    sx2, sy2 = map_model_point_to_segment(
        x2, y2,
        segment_width=segment_width, segment_height=segment_height,
        model_width=model_width, model_height=model_height,
    )
    segment_px = euclidean_pixel_distance(sx1, sy1, sx2, sy2)
    return pixel_length_to_cm(segment_px, pixels_per_cm)


# ==============================================================================
# بخش دوم: استخراج خط‌کش (ruler) و تخمین pixels_per_cm
# ==============================================================================

def _extract_ruler_info(     #از طریق خطکش کناری میگه هر سانتی متر چند پیکسله
    image_bgr: np.ndarray,
    ruler_width_ratio: float = 0.25,
) -> tuple[float | None, list[int], int, int]:
    """
    استخراج اطلاعات خط‌کش از تصویر B-mode.

    منطق:
      ۱) برش ۲۵٪ سمت راست تصویر
      ۲) تبدیل به grayscale و equalizeHist برای افزایش کنتراست
      ۳) آستانه‌گذاری (threshold > 200) برای پیدا کردن نوار سفید خط‌کش
      ۴) ستون با بیشترین پیکسل سفید → موقعیت X خط‌کش
      ۵) در یک باند ±۲۵ پیکسلی اطراف خط‌کش، contourهای کوچک (tick) پیدا می‌شوند
      ۶) فاصله میانه tickها تقسیم بر ۵ → pixels_per_cm

    ورودی:
        image_bgr        : تصویر BGR (اولین فریم ویدیو)
        ruler_width_ratio: نسبت عرض ناحیه خط‌کش (پیش‌فرض ۰.۲۵ = ۲۵٪)

    خروجی:
        (pixels_per_cm, tick_positions, x_global_ruler, x_start)
          - pixels_per_cm  : float یا None (اگر خط‌کش پیدا نشد)
          - tick_positions : لیست Y مراکز tickها (مرتب‌شده)
          - x_global_ruler : موقعیت X خط‌کش در تصویر اصلی
          - x_start        : شروع ناحیه ROI در تصویر اصلی
    """
    h, w = image_bgr.shape[:2]
    x_start = int(w * (1.0 - ruler_width_ratio))      # شروع ۲۵٪ سمت راست
    roi = image_bgr[:, x_start:w]

    # تبدیل به grayscale و افزایش کنتراست
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)   #Histogram Equalization: اگه نور کم بود یخش خط کش رو واضح میکنه

    # آستانه‌گذاری: پیکسل‌های خیلی روشن → سفید (خط‌کش)
    _, th = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # ستونی که بیشترین پیکسل سفید را دارد → موقعیت خط‌کش در ROI
    column_sum = np.sum(th, axis=0)    #تعداد پیکسلهای سفید هر ستون
    if np.max(column_sum) == 0:
        return None, [], 0, x_start                   # هیچ پیکسل سفیدی پیدا نشد

    x_ruler = int(np.argmax(column_sum))   #اندیس بیشترین مقدار ارایه یعنی میگه کدوم ستون بیشترین سفید رو داره

    # برش باند ±۲۵ پیکسلی اطراف محور خط‌کش برای جستجوی tickها
    band = 25
    x1 = max(0, x_ruler - band)
    x2 = min(roi.shape[1], x_ruler + band)
    ruler_roi = th[:, x1:x2]

    # پیدا کردن contourها و فیلتر tickها: عرض ۶ تا ۴۰ پیکسل، ارتفاع کمتر از ۶
    contours, _ = cv2.findContours(ruler_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tick_positions = sorted(
        y + hc // 2                                   # مرکز عمودی tick
        for (x, y, wc, hc) in map(cv2.boundingRect, contours)
        if 6 < wc < 40 and hc < 6
    )
    # tick_positions = [120, 263, 406, 549, 692, ...]

    x_global_ruler = x_start + x_ruler

    if len(tick_positions) < 2:
        return None, tick_positions, x_global_ruler, x_start   # حداقل دو tick لازم است

    # هر دو tick متوالی = ۵ سانتی‌متر → median(فاصله‌ها) / 5
    distances = np.diff(tick_positions)               # مثلاً [143, 143, 143, ...]
    pixels_per_cm = float(np.median(distances)) / 5.0 # 143 / 5 = 28.6

    return pixels_per_cm, tick_positions, x_global_ruler, x_start


def estimate_pixels_per_cm_from_bgr(
    image_bgr: np.ndarray,
    *,
    default_pixels_per_cm: float,
    ruler_width_ratio: float = 0.25,
) -> tuple[float, ScaleSource]:
    """
    تخمین مقیاس (pixels per cm) از تصویر B-mode.
    ورودی این تابع همون فریم اولی که processing.process_video از cv2.VideoCapture می‌خونه.

    ورودی:
        image_bgr            : تصویر BGR (اولین فریم ویدیو)
        default_pixels_per_cm: مقیاس پیش‌فرض (اگر خط‌کش پیدا نشد)
        ruler_width_ratio    : نسبت عرض ناحیه خط‌کش

    خروجی:
        (pixels_per_cm, source)
          - pixels_per_cm: مثلاً 28.60 (a4c) یا 32.60 (plax) یا مقدار پیش‌فرض
          - source       : "ruler_estimate" یا "default"
    """
    if default_pixels_per_cm <= 0:
        raise ValueError("default_pixels_per_cm must be positive.")

    # --- تصویر نامعتبر یا خیلی کوچک → مستقیم مقدار پیش‌فرض، حتی سراغ الگوریتم خط‌کش نمی‌ره ---
    if image_bgr is None or image_bgr.size == 0:
        return default_pixels_per_cm, "default"
    h, w = image_bgr.shape[:2]
    if h < 64 or w < 64:
        return default_pixels_per_cm, "default"

    # --- می‌ره داخل _extract_ruler_info و تلاش می‌کنه خط‌کش رو در تصویر پیدا کنه ---
    pixels_per_cm, _, _, _ = _extract_ruler_info(image_bgr, ruler_width_ratio)

    # اعتبارسنجی: مقیاس کمتر از ۱ پیکسل بر سانتی‌متر بی‌معنی است → fallback به پیش‌فرض
    if pixels_per_cm is None or pixels_per_cm <= 1.0:
        return default_pixels_per_cm, "default"

    return float(pixels_per_cm), "ruler_estimate"


# ==============================================================================
# بخش سوم: مصورسازی (Visualization) — برای دیباگ بصری نتیجه‌ی تشخیص خط‌کش
# ==============================================================================

def visualize_scale_result(
    image_bgr: np.ndarray,
    pixels_per_cm: float,                          # 28.60
    source: str,                                   # "ruler_estimate"
    save_path: str | os.PathLike | None = None,    # "debug_scale_output.jpg"
    show: bool = False,
    ruler_width_ratio: float = 0.25,
):
    """
    رسم تصویر دیباگ برای تأیید صحت تشخیص خط‌کش.

    عناصر رسم‌شده:
      ۱) سایه آبی روی ناحیه خط‌کش (۲۵٪ راست)
      ۲) خط عمودی زرد روی محور خط‌کش
      ۳) نقاط قرمز روی tickهای شناسایی‌شده و خطوط آبی بین آن‌ها
      ۴) خطوط افقی سبز هر ۱ سانتی‌متر (grid مجازی)
      ۵) متن اطلاعات: "Scale: 28.60 px/cm (ruler_estimate)"

    ورودی:
        image_bgr    : تصویر اصلی
        pixels_per_cm: مقیاس تخمین‌زده‌شده
        source       : منبع مقیاس ("ruler_estimate" / "default")
        save_path    : مسیر ذخیره تصویر دیباگ (اختیاری)
        show         : اگر True، تصویر در پنجره نمایش داده می‌شود
    """
    vis_img = image_bgr.copy()
    h, w = vis_img.shape[:2]

    # استخراج مجدد اطلاعات خط‌کش برای رسم
    _, ticks, x_global_ruler, x_start = _extract_ruler_info(image_bgr, ruler_width_ratio)

    # ۱) سایه زدن ناحیه خط‌کش (آبی تیره نیمه‌شفاف)
    overlay = vis_img.copy()
    cv2.rectangle(overlay, (x_start, 0), (w, h), (40, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, vis_img, 0.6, 0, vis_img)

    # ۲) محور اصلی خط‌کش (خط عمودی زرد)
    if x_global_ruler > 0:
        cv2.line(vis_img, (x_global_ruler, 0), (x_global_ruler, h), (0, 255, 255), 2)

    # ۳) نقاط tick (دایره قرمز) و خطوط آبی بین آن‌ها
    points = [(x_global_ruler, y) for y in ticks]
    for point in points:
        cv2.circle(vis_img, point, 5, (0, 0, 255), -1)
    for start, end in zip(points, points[1:]):
        cv2.line(vis_img, start, end, (255, 0, 0), 2)

    # ۴) grid یک سانتی‌متری: خطوط افقی سبز، هم‌تراز با اولین tick
    if pixels_per_cm > 0 and ticks:
        first_y = ticks[0] % pixels_per_cm            # اولین خط grid از بالای تصویر
        for grid_y in np.arange(first_y, h, pixels_per_cm):
            cv2.line(vis_img, (x_start, int(grid_y)), (w, int(grid_y)), (0, 255, 0), 1)

    # ۵) متن اطلاعات با پس‌زمینه مشکی
    text = f"Scale: {pixels_per_cm:.2f} px/cm ({source})"
    cv2.rectangle(vis_img, (10, 10), (450, 50), (0, 0, 0), -1)
    cv2.putText(vis_img, text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    if save_path:
        cv2.imwrite(str(save_path), vis_img)
        print(f"Scale debug image saved to: {save_path}")

    if show:
        cv2.imshow("Scale Debug", vis_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

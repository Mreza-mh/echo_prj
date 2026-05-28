"""
Apical four-chamber style atrial area segmentation (pixel + cm²).

Used by `main.py` when the detected view is `a4c`. Requires a B-mode crop (BGR)
and `pixels_per_cm` on that image (same calibration as linear measurements).
"""

# این فایل برای نمای A4C سطح دهلیزها را حساب می‌کند و خروجی تصویری و JSON آن را می‌سازد.
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from pipeline.measurement.scale import pixel_area_to_cm2


def frangi_vesselness(gray: np.ndarray, sigmas: list[float] | None = None, beta: float = 0.5, c: float = 15) -> np.ndarray:
    """
    فیلتر Frangi برای تشخیص ساختارهای لوله‌ای/عروقی در تصویر.
    
    منطق:
      - در چند مقیاس (sigma)، مشتقات دوم تصویر محاسبه می‌شود.
      - مقادیر ویژه Hessian تحلیل می‌شود.
      - ساختارهای ridge مانند (عروق) امتیاز بالاتری می‌گیرند.
    
    ورودی:
        gray  : تصویر grayscale
        sigmas: لیست مقیاس‌ها (پیش‌فرض [1.0, 2.0, 3.0])
        beta  : پارامتر حساسیت به ساختارهای blob-like (پیش‌فرض 0.5)
        c     : پارامتر حساسیت به نویز (پیش‌فرض 15)
    
    خروجی:
        np.ndarray با مقادیر 0-255 (vesselness map)
    """
    if sigmas is None:
        sigmas = [1.0, 2.0, 3.0]

    float_img = gray.astype(np.float64) / 255.0                      # نرمال‌سازی [0,1]
    h, w = float_img.shape
    vesselness = np.zeros((h, w), dtype=np.float64)

    for sigma in sigmas:
        ksize = int(2 * round(4 * sigma) + 1)                        # اندازه کرنل Gauss
        blur = cv2.GaussianBlur(float_img, (ksize, ksize), sigma, borderType=cv2.BORDER_REFLECT)

        # مشتقات مرتبه اول و دوم
        ix = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        iy = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
        ixx = cv2.Sobel(ix, cv2.CV_64F, 1, 0, ksize=3)
        ixy = cv2.Sobel(ix, cv2.CV_64F, 0, 1, ksize=3)
        iyy = cv2.Sobel(iy, cv2.CV_64F, 0, 1, ksize=3)

        # مقادیر ویژه Hessian
        tmp = np.sqrt((ixx - iyy) ** 2 + 4 * ixy**2)
        lambda1 = (ixx + iyy + tmp) / 2.0
        lambda2 = (ixx + iyy - tmp) / 2.0

        # مرتب‌سازی: |lambda2| >= |lambda1|
        mask = np.abs(lambda1) > np.abs(lambda2)
        lbig = np.where(mask, lambda1, lambda2)
        lsmall = np.where(mask, lambda2, lambda1)
        lambda2 = lbig
        lambda1 = lsmall

        vessel = np.zeros_like(float_img)
        ridge = lambda2 < 0                                            # فقط ridge ها
        if np.any(ridge):
            rb = np.abs(lambda1[ridge]) / (np.abs(lambda2[ridge]) + 1e-6)
            s = np.sqrt(lambda1[ridge] ** 2 + lambda2[ridge] ** 2)
            v = np.exp(-(rb**2) / (2 * beta**2)) * (1 - np.exp(-(s**2) / (2 * c**2)))
            vessel[ridge] = v
        vesselness = np.maximum(vesselness, vessel)                    # max over scales

    # نرمال‌سازی به [0, 255]
    if vesselness.max() > 0:
        vesselness = (vesselness / vesselness.max() * 255).astype(np.uint8)
    else:
        vesselness = vesselness.astype(np.uint8)
    return vesselness


def deform_line_to_edges(
    img_gray: np.ndarray,
    pt1: tuple[int, int],
    pt2: tuple[int, int],
    num_points: int = 30,
    search_range: int = 15,
    iterations: int = 10,
) -> list[tuple[int, int]]:
    """
    تغییر شکل یک خط مستقیم به سمت لبه‌های تصویر (Active Contour ساده).
    
    منطق:
      - خط اولیه بین pt1 و pt2 با num_points نقطه نمونه‌برداری می‌شود.
      - در هر iteration، هر نقطه در جهت عمود بر خط حرکت می‌کند
        به سمتی که گرادیان تصویر بیشینه باشد.
    
    ورودی:
        img_gray    : تصویر grayscale
        pt1, pt2    : نقاط ابتدا و انتهای خط
        num_points  : تعداد نقاط نمونه‌برداری
        search_range: شعاع جستجو برای هر نقطه
        iterations  : تعداد تکرار
    
    خروجی:
        لیست (x,y) نقاط تغییرشکل‌یافته
    """
    # نمونه‌برداری خط اولیه
    x_vals = np.linspace(pt1[0], pt2[0], num_points).astype(np.int32)
    y_vals = np.linspace(pt1[1], pt2[1], num_points).astype(np.int32)
    points = list(zip(x_vals.tolist(), y_vals.tolist()))

    # گرادیان تصویر
    grad_x = cv2.Sobel(img_gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)                        # اندازه گرادیان
    h, w = img_gray.shape

    for _ in range(iterations):
        new_points = points.copy()
        for i in range(1, len(points) - 1):                           # نقاط میانی (نه ابتدا/انتها)
            px, py = points[i]
            prev_pt = points[i - 1]
            next_pt = points[i + 1]

            # بردار جهت خط
            dx = next_pt[0] - prev_pt[0]
            dy = next_pt[1] - prev_pt[1]
            length = math.hypot(dx, dy)
            if length == 0:
                continue

            # بردار عمود (نرمال)
            nx = -dy / length
            ny = dx / length

            # جستجوی بهترین موقعیت در راستای عمود
            best_val = -1.0
            best_off = 0
            for off in range(-search_range, search_range + 1):
                cx = int(px + nx * off)
                cy = int(py + ny * off)
                if 0 <= cx < w and 0 <= cy < h:
                    val = float(grad_mag[cy, cx])
                    if val > best_val:
                        best_val = val
                        best_off = off

            new_points[i] = (int(px + nx * best_off), int(py + ny * best_off))
        points = new_points
    return points


def get_seed_points_from_rays(
    best_center: tuple[int, int],          # مرکز تخمینی قلب
    best_rays: list[tuple[int, int]],      # ۴ نقطه انتهایی پرتوها (راست، پایین، چپ، بالا)
    gray_img: np.ndarray,                  # تصویر grayscale
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    تخمین نقاط seed برای دهلیز چپ و راست بر اساس پرتوهای بهینه.
    
    منطق:
      - دهلیز راست ≈ میانگین پرتوهای راست و پایین
      - دهلیز چپ  ≈ میانگین پرتوهای چپ و پایین
      - سپس refinement: در یک شعاع ۲۰ پیکسلی، تاریک‌ترین نقطه را پیدا می‌کند
        (چون دهلیزها پر از خون هستند و تیره دیده می‌شوند)
    
    خروجی:
        (left_seed, right_seed): مختصات نقاط شروع برای flood fill
    """
    cx, cy = best_center
    e_r, e_d, e_l, e_u = best_rays

    # حدس اولیه برای دهلیز چپ (بین چپ و پایین)
    guess_left_x = int((cx + e_l[0] + e_d[0]) / 3)
    guess_left_y = int((cy + e_l[1] + e_d[1]) / 3)

    # حدس اولیه برای دهلیز راست (بین راست و پایین)
    guess_right_x = int((cx + e_r[0] + e_d[0]) / 3)
    guess_right_y = int((cy + e_r[1] + e_d[1]) / 3)

    def refine_seed(x: int, y: int, img: np.ndarray, radius: int = 20) -> tuple[int, int]:
        """پیدا کردن تاریک‌ترین نقطه در همسایگی"""
        hh, ww = img.shape
        min_val = 255
        best_pt = (x, y)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < ww and 0 <= ny < hh:
                    if img[ny, nx] < min_val:
                        min_val = int(img[ny, nx])
                        best_pt = (nx, ny)
        return best_pt

    return (
        refine_seed(guess_left_x, guess_left_y, gray_img),     # seed چپ
        refine_seed(guess_right_x, guess_right_y, gray_img)    # seed راست
    )


def find_chamber_mask_and_centroid(
    seed: tuple[int, int],               # نقطه شروع
    boundary_mask: np.ndarray,           # ماسک مرزها
) -> tuple[np.ndarray | None, tuple[int, int] | None]:
    """
    پیدا کردن ناحیه یک حفره با Flood Fill از نقطه seed.
    
    منطق:
      - از seed شروع می‌کند و تمام پیکسل‌های متصل که مقدار ۰ دارند را
        با ۱۲۸ پر می‌کند (در محدوده ماسک مرزها).
      - مرکز جرم ناحیه پر شده محاسبه می‌شود.
    
    خروجی:
        (mask, centroid): ماسک باینری ناحیه و مختصات مرکز جرم
        یا (None, None) اگر flood fill موفق نبود
    """
    flood_mask = boundary_mask.copy()
    h, w = flood_mask.shape
    mask_ff = np.zeros((h + 2, w + 2), np.uint8)                    # ماسک برای floodFill
    cv2.floodFill(flood_mask, mask_ff, seed, 128)                   # پر کردن با ۱۲۸
    chamber = (flood_mask == 128).astype(np.uint8)                   # ماسک باینری
    m = cv2.moments(chamber)
    if m["m00"] == 0:
        return None, None
    cx = int(m["m10"] / m["m00"])                                    # مرکز جرم X
    cy = int(m["m01"] / m["m00"])                                    # مرکز جرم Y
    return chamber, (cx, cy)


def run_a4c_atrial_areas(
    image_bgr: np.ndarray,                # تصویر BGR از فریم a4c
    pixels_per_cm: float,                 # 28.6 (مقیاس تخمین‌زده‌شده)
    *,
    exclusion_radius: int = 70,           # شعاع Exclusion اطراف مرکز
    use_frangi: bool = False,             # آیا از فیلتر Frangi استفاده شود؟
    use_active_contour: bool = True,      # آیا از Active Contour استفاده شود؟
    output_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """
    محاسبه مساحت دهلیز چپ و راست در نمای A4C.
    
    مراحل:
      ۱) پیدا کردن مرکز و ۴ پرتو بهینه
      ۲) آستانه‌گذاری و یافتن کانتورها
      ۳) اتصال نقاط انتهایی نزدیک (bridge)
      ۴) Active Contour برای بهبود مرزها
      ۵) Flood Fill برای جداسازی دهلیزها
      ۶) محاسبه مساحت به cm² و رسم overlay
    
    خروجی (مقادیر واقعی از لاگ):
        {
            "pixels_per_cm": 28.6,
            "best_center": {"x": 306, "y": 253},
            "areas_px": {"right_atrium": 9054, "left_atrium": 17384},
            "areas_cm2": {
                "right_atrium": 11.066555821800577,
                "left_atrium": 21.252873001124748
            },
            "saved_paths": {
                "overlay_png": "C:\\...\\a4c_atrial_overlay.png",
                "areas_json": "C:\\...\\a4c_area_cm2.json"
            }
        }
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")

    h, w = image_bgr.shape[:2]                                       # (507, 612)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur_rays = cv2.GaussianBlur(gray, (15, 15), 0)                 # برای پرتوها

    def best_ray(cx: int, cy: int, angles: range, length: int) -> tuple[float, tuple[int, int]]:
        """پیدا کردن بهترین پرتو در یک محدوده زاویه"""
        maxv = -1.0
        best_end = (cx, cy)
        for a in angles:
            rad = math.radians(a)
            dx, dy = length * math.cos(rad), length * math.sin(rad)
            xs = np.linspace(cx, cx + dx, int(length)).astype(int)
            ys = np.linspace(cy, cy + dy, int(length)).astype(int)
            valid = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
            if not np.any(valid):
                continue
            val = float(np.mean(blur_rays[ys[valid], xs[valid]]))   # میانگین روشنایی
            if val > maxv:
                maxv = val
                best_end = (int(cx + dx), int(cy + dy))
        return maxv, best_end

    # جستجوی مرکز و پرتوهای بهینه
    length = int(h * 0.33)                                           # طول پرتو ≈ یک‌سوم ارتفاع
    best_center = (w // 2, h // 2)                                   # حدس اولیه: مرکز تصویر
    best_score = -1.0
    best_rays: list[tuple[int, int]] = []

    # جستجو در یک پنجره اطراف مرکز
    for cy in range(int(h * 0.4), int(h * 0.7), 5):
        for cx in range(int(w * 0.4), int(w * 0.6), 5):
            s_r, e_r = best_ray(cx, cy, range(-30, 31, 2), length)   # راست
            s_d, e_d = best_ray(cx, cy, range(60, 121, 2), length)   # پایین
            s_l, e_l = best_ray(cx, cy, range(150, 211, 2), length)  # چپ
            s_u, e_u = best_ray(cx, cy, range(240, 301, 2), length)  # بالا
            tot = s_r + s_d + s_l + s_u
            if tot > best_score:
                best_score = tot
                best_center = (cx, cy)
                best_rays = [e_r, e_d, e_l, e_u]
    # best_center = (306, 253)

    # ---- آستانه‌گذاری و morphological opening ----
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blur, 75, 255, cv2.THRESH_BINARY)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open)

    # (اختیاری) افزودن vesselness به ماسک
    if use_frangi:
        vesselness = frangi_vesselness(gray)
        _, vessel_mask = cv2.threshold(vesselness, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cleaned = cv2.bitwise_or(cleaned, vessel_mask)

    # ---- یافتن نقاط انتهایی کانتورها ----
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    endpoints: list[tuple[int, int]] = []
    for cnt in contours:
        if cv2.contourArea(cnt) > 200:
            ext_left = tuple(cnt[cnt[:, :, 0].argmin()][0])
            ext_right = tuple(cnt[cnt[:, :, 0].argmax()][0])
            ext_top = tuple(cnt[cnt[:, :, 1].argmin()][0])
            ext_bot = tuple(cnt[cnt[:, :, 1].argmax()][0])
            endpoints.extend([ext_left, ext_right, ext_top, ext_bot])

    # ---- اتصال نقاط نزدیک (bridge) ----
    bridged_walls = cleaned.copy()
    max_gap = 80
    min_gap = 20
    bridge_pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            pt1, pt2 = endpoints[i], endpoints[j]
            dist1 = math.hypot(pt1[0] - best_center[0], pt1[1] - best_center[1])
            dist2 = math.hypot(pt2[0] - best_center[0], pt2[1] - best_center[1])
            mid = ((pt1[0] + pt2[0]) / 2, (pt1[1] + pt2[1]) / 2)
            dist_mid = math.hypot(mid[0] - best_center[0], mid[1] - best_center[1])
            if dist1 < exclusion_radius or dist2 < exclusion_radius or dist_mid < exclusion_radius:
                continue                                             # نزدیک مرکز ← رد
            d = math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
            if min_gap < d < max_gap:
                cv2.line(bridged_walls, pt1, pt2, 255, 3)           # پل زدن
                bridge_pairs.append((pt1, pt2))

    # ---- Active Contour (Snake) روی پل‌ها ----
    if use_active_contour and bridge_pairs:
        snake_walls = bridged_walls.copy()
        for pt1, pt2 in bridge_pairs:
            new_pts = deform_line_to_edges(
                gray, pt1, pt2,
                num_points=max(10, int(math.hypot(pt2[0] - pt1[0], pt2[1] - pt1[1]) // 3)),
                search_range=15,
                iterations=8,
            )
            for k in range(1, len(new_pts)):
                cv2.line(snake_walls, new_pts[k - 1], new_pts[k], 255, 2)
        bridged_walls = snake_walls

    # ---- Morphological closing ----
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed_walls = cv2.morphologyEx(bridged_walls, cv2.MORPH_CLOSE, kernel_close)

    # رسم پرتوها روی ماسک
    for ep in best_rays:
        cv2.line(closed_walls, best_center, ep, 255, 3)

    # ---- Flood Fill برای جداسازی دهلیزها ----
    left_seed, right_seed = get_seed_points_from_rays(best_center, best_rays, blur_rays)
    mask_l, _cent_l = find_chamber_mask_and_centroid(left_seed, closed_walls)
    mask_r, _cent_r = find_chamber_mask_and_centroid(right_seed, closed_walls)

    # ---- محاسبه مساحت‌ها ----
    areas_px: dict[str, int] = {}
    if mask_r is not None:
        areas_px["right_atrium"] = int(np.sum(mask_r))               # 9054
    if mask_l is not None:
        areas_px["left_atrium"] = int(np.sum(mask_l))                # 17384

    scale = float(pixels_per_cm)                                      # 28.6
    areas_cm2 = {k: pixel_area_to_cm2(px, scale) for k, px in areas_px.items()}
    # areas_cm2 = {
    #     "right_atrium": 11.066555821800577,
    #     "left_atrium": 21.252873001124748
    # }

    # ---- ساخت تصویر overlay ----
    overlay = image_bgr.copy()

    # نمایش ماسک دیوارها (سفید نیمه‌شفاف)
    overlay[closed_walls == 255] = (
        0.85 * overlay[closed_walls == 255] + 0.15 * np.array([255, 255, 255])
    ).astype(np.uint8)

    # رسم پرتوها
    for ep in best_rays:
        cv2.line(overlay, best_center, ep, (255, 200, 0), 2)         # آبی فیروزه‌ای

    def draw_chamber(mask: np.ndarray | None, color_fill: tuple[float, float, float], name: str) -> None:
        """رسم یک دهلیز با رنگ مشخص و متن مساحت"""
        if mask is None:
            return
        # رنگ‌آمیزی ناحیه
        overlay[mask == 1] = (
            0.6 * overlay[mask == 1] + 0.4 * np.array(color_fill)
        ).astype(np.uint8)
        # کانتور
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, cnts, -1, (0, 0, 255), 1)         # قرمز
        # متن مساحت
        cm2_val = areas_cm2.get(name, 0.0)
        m = cv2.moments(mask)
        if m["m00"] != 0:
            c_x = int(m["m10"] / m["m00"])
            c_y = int(m["m01"] / m["m00"])
            cv2.putText(
                overlay, f"{cm2_val:.1f} cm2",
                (c_x - 30, c_y + 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (255, 255, 255), 1, cv2.LINE_AA
            )

    # رسم دهلیز راست (آبی) و چپ (قرمز تیره)
    draw_chamber(mask_r, (0, 0, 200), "right_atrium")
    draw_chamber(mask_l, (200, 0, 0), "left_atrium")

    # نقاط seed
    cv2.circle(overlay, right_seed, 4, (0, 255, 0), -1)              # سبز
    cv2.circle(overlay, left_seed, 4, (0, 255, 0), -1)               # سبز

    # دایره Exclusion
    circle_overlay = overlay.copy()
    cv2.circle(circle_overlay, best_center, exclusion_radius, (255, 255, 255), 1)
    cv2.addWeighted(circle_overlay, 0.3, overlay, 0.7, 0, overlay)

    # ---- ذخیره خروجی‌ها ----
    saved_paths: dict[str, str] = {}
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        overlay_path = out / "a4c_atrial_overlay.png"
        json_path = out / "a4c_area_cm2.json"

        cv2.imwrite(str(overlay_path), overlay)

        payload = {
            "pixels_per_cm": scale,
            "areas_cm2": areas_cm2,
            "areas_px": areas_px
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        saved_paths["overlay_png"] = str(overlay_path)
        saved_paths["areas_json"] = str(json_path)

    return {
        "pixels_per_cm": scale,
        "best_center": {"x": int(best_center[0]), "y": int(best_center[1])},  # (306, 253)
        "areas_px": areas_px,
        "areas_cm2": areas_cm2,
        "saved_paths": saved_paths,
    }
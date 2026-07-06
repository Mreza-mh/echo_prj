"""
این فایل ایونت‌های مهم را با استفاده از سیگنال ECG پیدا می‌کند
و فریم هر ایونت را برای مرحله اندازه‌گیری ذخیره می‌کند.

مراحل کلی:
  ۱) سیگنال ECG را با ردیابی نوار سبز رنگ در ناحیه پایین تصویر استخراج می‌کند.
  ۲) با Savitzky-Golay سیگنال را هموار می‌کند.
  ۳) قله‌های R را پیدا می‌کند، سپس Q, S, P, T و شروع/پایان آنها را تعیین می‌کند.
  ۴) بر اساس required_events فریم‌های مناسب را انتخاب می‌کند:
       End Diastol  →  شروع موج P
       LVOT         →  انتهای موج S
       End Sistol   →  انتهای موج T
  ۵) فریم‌های اصلی ویدیو را crop کرده و ذخیره می‌کند.
  ۶) نمودار ECG رسم و ذخیره می‌شود.
  ۷) CSV رویدادها (event_frames.csv) تولید می‌شود.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

# ==============================================================================
# تنظیمات / ثابت‌ها
# ==============================================================================

# نسبت‌های crop برای حذف حاشیه‌های اضافی از فریم اکو
CROP_Y1 = 0.085   # 8.5% از بالا
CROP_Y2 = 0.93    # 93% از بالا → 7% از پایین حذف می‌شود
CROP_X1 = 0.095   # 9.5% از چپ
CROP_X2 = 0.86    # 86% از چپ → 14% از راست حذف می‌شود

# ناحیه مورد نظر برای ردیابی نوار سبز ECG (پایین تصویر)
ROI_Y1 = 0.88     # 88% از بالا → نوار ECG معمولاً پایین صفحه است
ROI_Y2 = 0.98     # 98% از بالا
ROI_X1 = 0.05     # 5% از چپ
ROI_X2 = 0.85     # 85% از چپ

# محدوده رنگ سبز در فضای HSV برای شناسایی نوار ECG
GREEN_LOWER_HSV = (35, 80, 40)    # حد پایین سبز
GREEN_UPPER_HSV = (85, 255, 255)  # حد بالای سبز

# پارامترهای فیلتر Savitzky-Golay برای هموارسازی سیگنال
SAVGOL_WINDOW = 5        # اندازه پنجره (باید فرد باشد)
SAVGOL_POLYORDER = 2     # درجه چندجمله‌ای

# پارامترهای تشخیص قله‌های R
R_PEAK_PROMINENCE = 15   # حداقل prominence قله
R_PEAK_DISTANCE = 50     # حداقل فاصله بین دو قله (بر حسب نمونه)

# ==============================================================================
# استخراج سیگنال ECG از ویدیو (ردیابی نوار سبز)
# ==============================================================================

def crop_echo_frame(frame: np.ndarray) -> np.ndarray:
    """
    حذف حاشیه‌های اضافی از فریم اکوکاردیوگرافی طبق نسبت‌های CROP_*.

    ورودی:
        frame: np.ndarray با shape (H, W, 3) — یک فریم BGR از ویدیو

    خروجی:
        np.ndarray — فریم crop شده
        مثلاً (1080, 1920, 3) → (913, 1469, 3)
    """
    height, width = frame.shape[:2]
    y1 = int(height * CROP_Y1)
    y2 = int(height * CROP_Y2)
    x1 = int(width * CROP_X1)
    x2 = int(width * CROP_X2)
    return frame[y1:y2, x1:x2]


def _pick_wavefront_y(y_coords: np.ndarray, prev_y_img: float | None) -> float:
    """
    انتخاب مختصات Y نماینده نوار ECG در یک ستون.

    منطق:
      - اگر نوار نازک باشد (ضخامت < ۵ پیکسل) → میانه Y کافی است.
      - اگر ضخیم باشد، بر اساس جهت حرکت سیگنال لبه مناسب انتخاب می‌شود:
          حرکت به بالا  → لبه بالا (min_y)
          حرکت به پایین → لبه پایین (max_y)
          نامشخص       → میانه

    ورودی:
        y_coords  : مختصات Y پیکسل‌های فعال این ستون
        prev_y_img: مقدار Y قبلی سیگنال در مختصات تصویر (None اگر اولین نمونه است)
    """
    min_y = np.min(y_coords)          # بالاترین نقطه نوار
    max_y = np.max(y_coords)          # پایین‌ترین نقطه نوار

    if max_y - min_y < 5 or prev_y_img is None:
        return float(np.median(y_coords))
    if min_y < prev_y_img - 2:
        return float(min_y)           # لبه بالا (سیگنال در حال صعود)
    if max_y > prev_y_img + 2:
        return float(max_y)           # لبه پایین (سیگنال در حال نزول)
    return float(np.median(y_coords))


def _extract_ecg_signal(video_path: Path) -> pd.DataFrame:
    """
    استخراج سیگنال ECG از نوار سبز رنگ پایین تصویر.

    منطق:
      - در هر فریم، ناحیه ROI (پایین تصویر) بررسی می‌شود.
      - پیکسل‌های سبز رنگ شناسایی می‌شوند (محدوده HSV).
      - تفاوت ماسک فعلی با ماسک قبلی (new_pixels) نشان‌دهنده حرکت نوار است.
      - موقعیت X نوار ردیابی می‌شود و موقعیت Y به عنوان مقدار سیگنال ثبت می‌شود.
      - برای مدیریت wrap (وقتی نوار از راست به چپ می‌پرد)، مختصات X بازمرتب می‌شود.

    خروجی:
        pd.DataFrame با ستون‌های:
          - Sample_Index : شماره نمونه (0, 1, 2, ...)
          - Frame_Number : شماره فریم ویدیو که سیگنال در آن ثبت شده
          - Signal_Value : مقدار سیگنال (ارتفاع نوار از پایین ROI)
    """
    cap = cv2.VideoCapture(str(video_path)) #open video
    if not cap.isOpened():
        raise FileNotFoundError(f"خطا در باز کردن ویدیو: {video_path}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))   # عرض ویدیو ( 1920)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # ارتفاع ویدیو ( 1080)

    # مختصات ناحیه ROI (پایین تصویر)
    y1, y2 = int(h * ROI_Y1), int(h * ROI_Y2)    #  y1=950, y2=1058
    x1, x2 = int(w * ROI_X1), int(w * ROI_X2)    #  x1=96, x2=1632
    roi_h = y2 - y1                              # ارتفاع ROI (حدود 108 پیکسل)
    roi_w = x2 - x1                              # عرض ROI (حدود 1536 پیکسل)

    lower_green = np.array(GREEN_LOWER_HSV)
    upper_green = np.array(GREEN_UPPER_HSV)
    noise_kernel = np.ones((2, 2), np.uint8)     # کرنل حذف نویز (morphological opening)

    previous_mask = None         # ماسک فریم قبلی (برای محاسبه تفاوت)
    signal_data: list[float] = []  # مقادیر سیگنال
    frame_data: list[int] = []     # شماره فریم‌های متناظر

    frame_count = 0              # شمارنده فریم (از ۱ شروع می‌شود)
    last_x = -1                  # آخرین موقعیت X نوار
    max_jump = int(roi_w * 0.1)  # حداکثر پرش مجاز نوار (۱۰٪ عرض ROI)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        roi = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        current_mask = cv2.inRange(hsv, lower_green, upper_green)   # ماسک پیکسل‌های سبز

        # فریم اول: هنوز ماسک قبلی نداریم
        if previous_mask is None:
            previous_mask = current_mask
            continue

        # پیکسل‌هایی که در فریم جدید سبز شده‌اند (یعنی نوار به آنها حرکت کرده)
        new_pixels = cv2.bitwise_and(current_mask, cv2.bitwise_not(previous_mask))
        previous_mask = current_mask

        # حذف نویز با morphological opening
        new_pixels = cv2.morphologyEx(new_pixels, cv2.MORPH_OPEN, noise_kernel)

        # ستون‌هایی که حداقل یک پیکسل فعال دارند
        active_xs = np.where(np.sum(new_pixels, axis=0) > 0)[0]
        if len(active_xs) == 0:
            continue

        # اولین بار → شروع از اولین ستون فعال
        if last_x == -1:
            last_x = active_xs[0]

        # فیلتر پرش‌های غیرعادی:
        #   - حرکت عادی به راست (کمتر از max_jump)
        #   - یا wrap: نوار از انتهای راست به ابتدای چپ برگشته باشد
        valid_xs = [
            x for x in active_xs
            if (x >= last_x and (x - last_x) < max_jump)
            or (last_x > roi_w - max_jump and x < max_jump)
        ]
        if not valid_xs:
            continue

        valid_xs = np.sort(valid_xs)

        # اگر اختلاف دو ستون خیلی زیاد باشد
        # /می‌فهمد که نوار از انتهای صفحه به ابتدای صفحه برگشته است.
        wrap_indices = np.where(np.diff(valid_xs) > roi_w / 2)[0]
        if len(wrap_indices) > 0:
            wrap_idx = wrap_indices[0]
            ordered_xs = np.concatenate((valid_xs[wrap_idx + 1:], valid_xs[:wrap_idx + 1]))
        else:
            ordered_xs = valid_xs

        # بررسی هر ستون
        for x in ordered_xs:
            # مختصات Y پیکسل‌های فعال در این ستون
            y_coords = np.where(current_mask[:, x] > 0)[0]
            if len(y_coords) == 0:
                continue

            prev_y_img = (roi_h - signal_data[-1]) if signal_data else None # up or down ? 
            final_y = _pick_wavefront_y(y_coords, prev_y_img) #هنگام صعود → لبه بالایی نوار
                                                                # هنگام نزول → لبه پایینی نوار

            # ثبت مقدار سیگنال (ارتفاع از پایین ROI)
            signal_data.append(roi_h - final_y)
            frame_data.append(frame_count)
            last_x = x

    cap.release()

    return pd.DataFrame({
        "Sample_Index": range(len(signal_data)),    # [0, 1, 2, ..., N-1]
        "Frame_Number": frame_data,                 # [1, 1, 2, 2, 3, ...]
        "Signal_Value": signal_data,                # مقادیر سیگنال ECG
    })


# ==============================================================================
# پیدا کردن onset/offset یک موج — با حرکت گام‌به‌گام از قله به چپ/راست
# ==============================================================================

def find_onset(signal, peak_idx, max_steps, wave_dir):
    """
    پیدا کردن نقطه شروع یک موج (onset) با حرکت به سمت چپ از قله.

    ورودی:
        signal   : آرایه سیگنال
        peak_idx : ایندکس قله
        max_steps: حداکثر تعداد گام جستجو
        wave_dir : 1 (موج مثبت مثل P) یا -1 (موج منفی مثل Q)

    منطق:
      - موج مثبت: تا وقتی سیگنال کاهشی است به چپ می‌رود؛ اولین افزایش = onset
      - موج منفی: تا وقتی سیگنال افزایشی است به چپ می‌رود؛ اولین کاهش = onset
    """
    idx = peak_idx
    for _ in range(max_steps):
        if idx <= 0:
            break
        if wave_dir == 1 and signal[idx - 1] > signal[idx]:
            break
        if wave_dir == -1 and signal[idx - 1] < signal[idx]:
            break
        idx -= 1
    return idx


def find_offset(signal, peak_idx, max_steps, wave_dir):
    """
    پیدا کردن نقطه پایان یک موج (offset) با حرکت به سمت راست از قله.

    ورودی:
        signal   : آرایه سیگنال
        peak_idx : ایندکس قله
        max_steps: حداکثر تعداد گام جستجو
        wave_dir : 1 (موج مثبت مثل T) یا -1 (موج منفی مثل S)

    منطق:
      - موج مثبت: تا وقتی سیگنال کاهشی است به راست می‌رود؛ اولین افزایش = offset
      - موج منفی: تا وقتی سیگنال افزایشی است به راست می‌رود؛ اولین کاهش = offset
    """
    idx = peak_idx
    for _ in range(max_steps):
        if idx >= len(signal) - 1:
            break
        if wave_dir == 1 and signal[idx + 1] > signal[idx]:
            break
        if wave_dir == -1 and signal[idx + 1] < signal[idx]:
            break
        idx += 1
    return idx


# ==============================================================================
# رسم نمودار + تشخیص قله‌ها و تعیین فریم رویدادها
# ==============================================================================

def _plot_ecg(
    output_dir: Path,
    sample_index,                    # df_signal["Sample_Index"]
    signal: np.ndarray,              # سیگنال هموارشده
    peaks: list[tuple],              # [(indices, style, label), ...] — قله‌های P/Q/R/S/T
    landmarks: list[tuple],          # [(indices, style, label), ...] — onset/offset ها
) -> None:
    """
    رسم و ذخیره نمودار مورفولوژی ECG در output_dir/ecg_plot.png.

    عناصر:
      - سیگنال هموارشده (خط مشکی)
      - قله‌های R (قرمز)، Q (زرد)، S (سبز)، P (آبی)، T (بنفش)
      - نقاط onset/offset با مارکر فلش (رویدادهای انتخاب‌شده)
    """
    plt.figure(figsize=(18, 8))
    plt.plot(sample_index, signal, color="black", linewidth=1)

    for indices, style, label in peaks:
        plt.plot(indices, signal[indices], style, label=label)

    for indices, style, label in landmarks:
        if indices:
            plt.plot(indices, signal[indices], style, label=label)

    plt.title("ECG Morphology Details")
    plt.xlabel("Sample Index")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.legend()
    plt.savefig(str(output_dir / "ecg_plot.png"), dpi=300)
    plt.close()


def _find_events_and_plot(
    df_signal: pd.DataFrame,        # خروجی _extract_ecg_signal
    output_dir: Path,               # پوشه ذخیره نمودار
    required_events: list[str],     # ['End Diastol', 'End Sistol', 'LVOT']
) -> dict[str, int]:
    """
    تشخیص قله‌های ECG و تعیین فریم‌های متناظر با رویدادهای درخواستی.

    مراحل:
      ۱) هموارسازی سیگنال با Savitzky-Golay
      ۲) تشخیص قله‌های R
      ۳) برای هر قله R: پیدا کردن Q, S, P, T و onset/offset آنها
      ۴) انتخاب آخرین چرخه کامل برای هر رویداد
      ۵) رسم و ذخیره نمودار ECG

    خروجی:
        dict: {'End Diastol': 60, 'End Sistol': 87}  (شماره فریم‌ها)
    """
    if df_signal.empty or len(df_signal) <= 15:
        raise ValueError("استخراج سیگنال ECG با شکست مواجه شد.")

    # هموارسازی سیگنال با فیلتر Savitzky-Golay (حذف نویز با حفظ شکل موج)
    df_signal["Smoothed_Signal"] = savgol_filter(
        df_signal["Signal_Value"],
        window_length=SAVGOL_WINDOW,
        polyorder=SAVGOL_POLYORDER,
    )
    signal = df_signal["Smoothed_Signal"].values

    # ----- تشخیص قله‌های R -----
    r_peaks, _ = find_peaks(signal, prominence=R_PEAK_PROMINENCE, distance=R_PEAK_DISTANCE)
    # r_peaks = [45, 98, 152, ...]  (ایندکس نمونه‌ها، نه شماره فریم)

    # لیست‌های نقاط کلیدی هر چرخه
    q_peaks, s_peaks, p_peaks, t_peaks = [], [], [], []
    p_starts, q_starts, s_ends, t_ends = [], [], [], []

    # ----- تحلیل هر چرخه قلبی (برای هر قله R) -----
    for r in r_peaks:
        # --- موج Q: مینیمم قبل از R (در بازه ۲۰ نمونه) ---
        q_search_start = max(0, r - 20)
        q = q_search_start + np.argmin(signal[q_search_start:r])
        q_peaks.append(q)
        q_starts.append(find_onset(signal, q, 15, -1))   # شروع Q (حرکت به چپ، موج منفی)

        # --- موج S: مینیمم بعد از R (در بازه ۲۰ نمونه) ---
        s_search_end = min(len(signal), r + 20)
        s = r + np.argmin(signal[r:s_search_end])
        s_peaks.append(s)
        s_ends.append(find_offset(signal, s, 15, -1))    # پایان S (حرکت به راست، موج منفی)

        # --- موج P: ماکزیمم قبل از Q (در بازه ۵ تا ۳۵ نمونه قبل از Q) ---
        p_search_start = max(0, q - 35)
        p_search_end = max(0, q - 5)
        if p_search_start < p_search_end:
            p = p_search_start + np.argmax(signal[p_search_start:p_search_end])
            p_peaks.append(p)
            p_starts.append(find_onset(signal, p, 20, 1))  # شروع P (حرکت به چپ، موج مثبت)

        # --- موج T: ماکزیمم بعد از S (در بازه ۱۰ تا ۵۰ نمونه بعد از S) ---
        t_search_start = min(len(signal) - 1, s + 10)
        t_search_end = min(len(signal), s + 50)
        if t_search_start < t_search_end:
            t = t_search_start + np.argmax(signal[t_search_start:t_search_end])
            t_peaks.append(t)
            t_ends.append(find_offset(signal, t, 30, 1))   # پایان T (حرکت به راست، موج مثبت)

    # ----- انتخاب فریم مناسب برای هر رویداد -----
    def get_frame(indices):
        """
        از بین ایندکس‌های یک رویداد (مثلاً تمام p_starts چرخه‌های مختلف)،
        آخرین چرخه را انتخاب می‌کند و شماره فریم متناظر را برمی‌گرداند.

        چرا آخرین؟ چون معمولاً کامل‌ترین و پایدارترین چرخه است.
        """
        if not indices:
            return None
        return int(df_signal["Frame_Number"].iloc[max(indices)])

    # نگاشت رویداد → فریم تشخیص‌داده‌شده:
    #   End Diastol = شروع موج P   (بیشترین حجم بطن)
    #   LVOT        = انتهای موج S (باز شدن دریچه آئورت)
    #   End Sistol  = انتهای موج T (کمترین حجم بطن)
    detected_frames = {
        "End Diastol": get_frame(p_starts),
        "LVOT":        get_frame(s_ends),
        "End Sistol":  get_frame(t_ends),
    }

    # fallback: فریم میانی ویدیو (اگر رویدادی پیدا نشد یا ناشناخته بود)
    fallback = int(df_signal["Frame_Number"].iloc[len(df_signal) // 2])

    event_frames = {
        event_name: detected_frames.get(event_name) or fallback
        for event_name in required_events
    }
    # مثلاً {'End Diastol': 60, 'End Sistol': 87} یا برای plax: {..., 'LVOT': 45}

    # ----- رسم و ذخیره نمودار ECG -----
    _plot_ecg(
        output_dir, df_signal["Sample_Index"], signal,
        peaks=[
            (r_peaks, "ro", "R"),
            (q_peaks, "yo", "Q"),
            (s_peaks, "go", "S"),
            (p_peaks, "bo", "P"),
            (t_peaks, "mo", "T"),
        ],
        landmarks=[
            (p_starts, "b>", "P Start (End Diastol)"),
            (q_starts, "y>", "Q Start"),
            (s_ends, "g<", "S End (LVOT)"),
            (t_ends, "m<", "T End (End Sistol)"),
        ],
    )

    return event_frames


# ==============================================================================
# ذخیره‌ی فریم‌های تصویری متناظر با هر رویداد
# ==============================================================================

def _save_event_images(
    video_path: Path,                # مسیر ویدیو
    output_dir: Path,                # پوشه خروجی
    event_frames: dict[str, int],    # {'End Diastol': 60, 'End Sistol': 87}
) -> dict[str, str]:
    """
    استخراج و ذخیره فریم‌های مربوط به رویدادها از ویدیو.

    مراحل:
      ۱) گروه‌بندی رویدادها بر اساس شماره فریم (چند رویداد ممکن است یک فریم باشند)
      ۲) پیمایش ویدیو تا رسیدن به فریم‌های مورد نظر
      ۳) crop کردن هر فریم و ذخیره آن

    خروجی:
        dict: {نام رویداد: مسیر مطلق فایل ذخیره‌شده}
        {'End Diastol': 'C:\\Users\\...\\End_Diastol\\frame_0060.jpg', ...}
    """
    # گروه‌بندی: هر شماره فریم → لیست رویدادهای آن
    # target_frames = {60: ['End Diastol'], 87: ['End Sistol']}
    target_frames: dict[int, list[str]] = {}
    for event_name, frame_number in event_frames.items():
        target_frames.setdefault(frame_number, []).append(event_name)

    max_frame_needed = max(event_frames.values()) if event_frames else 0

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {}

    current_frame = 1      # شمارنده فریم (از ۱ شروع می‌شود)
    saved_paths = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if current_frame in target_frames:
            cropped_frame = crop_echo_frame(frame)          # حذف حاشیه‌ها
            for event_name in target_frames[current_frame]:
                # ساخت پوشه رویداد: .../events/End_Diastol/
                event_dir = output_dir / event_name.replace(" ", "_")
                event_dir.mkdir(parents=True, exist_ok=True)

                # ذخیره فریم: frame_0060.jpg
                img_path = event_dir / f"frame_{current_frame:04d}.jpg"
                cv2.imwrite(str(img_path), cropped_frame)
                saved_paths[event_name] = str(img_path.resolve())

        if current_frame >= max_frame_needed:
            break
        current_frame += 1

    cap.release()
    return saved_paths


# ==============================================================================
# extract_events — نقطه‌ی ورود این ماژول؛ processing.process_video مستقیم همینو صدا می‌زنه
# ==============================================================================

def extract_events(
    video_path: str | Path,           # 'C:\\Users\\...\\dd.avi'
    output_dir: str | Path,           # 'C:\\Users\\...\\internal\\events'
    required_events: list[str],       # ['End Diastol', 'End Sistol']
) -> dict:
    """
    تابع اصلی استخراج رویدادهای ECG.

    مراحل:
    ۱) استخراج سیگنال ECG از ویدیو
    ۲) تحلیل سیگنال و یافتن فریم‌های رویدادها
    ۳) استخراج و ذخیره فریم‌های مربوطه
    ۴) تولید CSV رویدادها

    خروجی:
        dict = {
            "total_frames": 102,
            "event_frames": {'End Diastol': 60, 'End Sistol': 87},
            "saved_frames": {
                'End Diastol': 'C:\\Users\\...\\frame_0060.jpg',
                'End Sistol': 'C:\\Users\\...\\frame_0087.jpg'
            }
        }
    """
    resolved_video = Path(video_path).expanduser().resolve()
    resolved_output = Path(output_dir).expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)

    # ---  1: extract_ecg_signal 
    df_signal = _extract_ecg_signal(resolved_video)

    # ---  2:   _find_events_and_plot → فریم‌های حساس + نمودار → {'End Diastol': 60, ...} ---
    event_frames = _find_events_and_plot(df_signal, resolved_output, required_events)

    # ---  3:   _save_event_images → بریدن و ذخیره فریم‌ها → {نام رویداد: مسیر تصویر} ---
    saved_frames = _save_event_images(resolved_video, resolved_output, event_frames)

    return {
        "total_frames": int(df_signal["Frame_Number"].max()) if not df_signal.empty else 0,
        "event_frames": event_frames,
        "saved_frames": saved_frames,
    }

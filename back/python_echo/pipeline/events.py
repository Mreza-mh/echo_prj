from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

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

# ===================== تنظیمات =====================

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

# ===================================================

def crop_echo_frame(frame: np.ndarray) -> np.ndarray:
    """
    حذف حاشیه‌های اضافی از فریم اکوکاردیوگرافی.
    
    ورودی:
        frame: np.ndarray با shape (H, W, 3) — یک فریم BGR از ویدیو
    
    خروجی:
        np.ndarray — فریم crop شده
        (حاشیه‌های بالا، پایین، چپ و راست طبق نسبت‌های CROP_* حذف می‌شوند)
    """
    height, width = frame.shape[:2]              # مثلاً (1080, 1920)
    y1 = int(height * CROP_Y1)                   # 91
    y2 = int(height * CROP_Y2)                   # 1004
    x1 = int(width * CROP_X1)                    # 182
    x2 = int(width * CROP_X2)                    # 1651
    return frame[y1:y2, x1:x2]                   # سایز خروجی: (913, 1469, 3)


def _extract_ecg_signal(video_path: Path) -> pd.DataFrame:
    """
    استخراج سیگنال ECG از نوار سبز رنگ پایین تصویر.
    
    منطق:
      - در هر فریم، ناحیه ROI (پایین تصویر) بررسی می‌شود.
      - پیکسل‌های سبز رنگ شناسایی می‌شوند (محدوده HSV).
      - تفاوت ماسک فعلی با ماسک قبلی (new_pixels) نشان‌دهنده حرکت نوار است.
      - موقعیت X نوار ردیابی می‌شود و موقعیت Y به عنوان مقدار سیگنال ثبت می‌شود.
      - برای مدیریت wrap (وقتی نوار از راست به چپ می‌پرد)، مختصات X بازمرتب می‌شود.
    
    ورودی:
        video_path: Path — مسیر فایل ویدیو
    
    خروجی:
        pd.DataFrame با ستون‌های:
          - Sample_Index  : شماره نمونه (0, 1, 2, ...)
          - Frame_Number  : شماره فریم ویدیو که سیگنال در آن ثبت شده
          - Signal_Value  : مقدار سیگنال (ارتفاع نوار از پایین ROI)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"خطا در باز کردن ویدیو: {video_path}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))   # عرض ویدیو (مثلاً 1920)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # ارتفاع ویدیو (مثلاً 1080)

    # محاسبه مختصات ناحیه ROI (پایین تصویر)
    y1, y2 = int(h * ROI_Y1), int(h * ROI_Y2)    # مثلاً y1=950, y2=1058
    x1, x2 = int(w * ROI_X1), int(w * ROI_X2)    # مثلاً x1=96, x2=1632

    roi_h = y2 - y1   # ارتفاع ROI (حدود 108 پیکسل)
    roi_w = x2 - x1   # عرض ROI (حدود 1536 پیکسل)

    lower_green = np.array(GREEN_LOWER_HSV)   # [ 35  80  40]
    upper_green = np.array(GREEN_UPPER_HSV)   # [ 85 255 255]

    previous_mask = None     # ماسک فریم قبلی (برای محاسبه تفاوت)
    signal_data = []         # لیست مقادیر سیگنال
    frame_data = []          # لیست شماره فریم‌های متناظر

    frame_count = 0          # شمارنده فریم
    last_x = -1              # آخرین موقعیت X نوار
    max_jump = int(roi_w * 0.1)  # حداکثر پرش مجاز نوار (۱۰٪ عرض ROI)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1                         # شماره فریم (از ۱ شروع می‌شود)
        roi = frame[y1:y2, x1:x2]                # برش ناحیه ROI
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)  # تبدیل به HSV
        current_mask = cv2.inRange(hsv, lower_green, upper_green)  # ماسک پیکسل‌های سبز

        if previous_mask is not None:
            # پیدا کردن پیکسل‌هایی که در فریم جدید سبز هستند ولی در فریم قبلی نبودند
            # (یعنی پیکسل‌هایی که نوار به آنها حرکت کرده)
            new_pixels = cv2.bitwise_and(current_mask, cv2.bitwise_not(previous_mask))

            # حذف نویز با morphological opening
            kernel = np.ones((2, 2), np.uint8)
            new_pixels = cv2.morphologyEx(new_pixels, cv2.MORPH_OPEN, kernel)

            # پیدا کردن ستون‌هایی که حداقل یک پیکسل فعال دارند
            active_xs = np.where(np.sum(new_pixels, axis=0) > 0)[0]

            if len(active_xs) > 0:
                # اولین بار → شروع از اولین ستون فعال
                if last_x == -1:
                    last_x = active_xs[0]

                # فیلتر کردن پرش‌های غیرعادی (بیشتر از max_jump)
                valid_xs = []
                for x in active_xs:
                    # حرکت عادی به راست
                    if (x >= last_x and (x - last_x) < max_jump):
                        valid_xs.append(x)
                    # wrap: اگر نوار از راست به چپ برگشته باشد
                    elif (last_x > roi_w - max_jump and x < max_jump):
                        valid_xs.append(x)

                if len(valid_xs) > 0:
                    valid_xs = np.sort(valid_xs)
                    diffs = np.diff(valid_xs)

                    # تشخیص wrap (پرش بزرگ در مختصات X)
                    wrap_indices = np.where(diffs > roi_w / 2)[0]

                    if len(wrap_indices) > 0:
                        # بازمرتب‌سازی: اول نقاط بعد از wrap، بعد نقاط قبل از wrap
                        wrap_idx = wrap_indices[0]
                        ordered_xs = np.concatenate(
                            (valid_xs[wrap_idx + 1:], valid_xs[:wrap_idx + 1])
                        )
                    else:
                        ordered_xs = valid_xs

                    for x in ordered_xs:
                        # مختصات Y پیکسل‌های فعال در این ستون
                        y_coords = np.where(current_mask[:, x] > 0)[0]
                        if len(y_coords) > 0:
                            min_y = np.min(y_coords)   # بالاترین نقطه
                            max_y = np.max(y_coords)   # پایین‌ترین نقطه
                            thickness = max_y - min_y   # ضخامت نوار

                            # اگر نوار نازک باشد → میانه Y
                            if thickness < 5:
                                final_y = np.median(y_coords)
                            else:
                                # انتخاب لبه مناسب بر اساس جهت حرکت
                                if len(signal_data) > 0:
                                    prev_y_img = roi_h - signal_data[-1]
                                    if min_y < prev_y_img - 2:
                                        final_y = min_y   # لبه بالا
                                    elif max_y > prev_y_img + 2:
                                        final_y = max_y   # لبه پایین
                                    else:
                                        final_y = np.median(y_coords)
                                else:
                                    final_y = np.median(y_coords)

                            # ثبت مقدار سیگنال (ارتفاع از پایین ROI)
                            signal_data.append(roi_h - final_y)
                            frame_data.append(frame_count)
                            last_x = x   # به‌روزرسانی آخرین موقعیت X

        previous_mask = current_mask.copy()

    cap.release()

    # خروجی: DataFrame با ۳ ستون
    return pd.DataFrame({
        "Sample_Index": range(len(signal_data)),    # [0, 1, 2, ..., N-1]
        "Frame_Number": frame_data,                 # [1, 2, 3, ..., 102]
        "Signal_Value": signal_data                 # مقادیر سیگنال ECG
    })
    # sample output (first 5 rows):
    #    Sample_Index  Frame_Number  Signal_Value
    # 0             0             1          45.2
    # 1             1             1          46.1
    # 2             2             2          47.3
    # 3             3             2          48.0
    # 4             4             3          46.8


def find_onset(signal, peak_idx, max_steps, wave_dir):
    """
    پیدا کردن نقطه شروع یک موج (onset) با حرکت به سمت چپ.
    
    ورودی:
        signal   : آرایه سیگنال
        peak_idx : ایندکس قله
        max_steps: حداکثر تعداد گام جستجو
        wave_dir : 1 (موج مثبت/بالارونده) یا -1 (موج منفی/پایین‌رونده)
    
    خروجی:
        ایندکس نقطه شروع (onset)
    
    منطق:
      - از قله به سمت چپ حرکت می‌کند.
      - برای wave_dir=1 (مثل موج P): تا جایی که سیگنال همچنان کاهشی است ادامه می‌دهد.
      - برای wave_dir=-1 (مثل موج Q): تا جایی که سیگنال همچنان افزایشی است ادامه می‌دهد.
    """
    idx = peak_idx
    for _ in range(max_steps):
        if idx <= 0:
            break
        # موج مثبت: وقتی سیگنال شروع به افزایش کند → onset پیدا شده
        if wave_dir == 1 and signal[idx - 1] > signal[idx]:
            break
        # موج منفی: وقتی سیگنال شروع به کاهش کند → onset پیدا شده
        if wave_dir == -1 and signal[idx - 1] < signal[idx]:
            break
        idx -= 1
    return idx


def find_offset(signal, peak_idx, max_steps, wave_dir):
    """
    پیدا کردن نقطه پایان یک موج (offset) با حرکت به سمت راست.
    
    ورودی:
        signal   : آرایه سیگنال
        peak_idx : ایندکس قله
        max_steps: حداکثر تعداد گام جستجو
        wave_dir : 1 (موج مثبت) یا -1 (موج منفی)
    
    خروجی:
        ایندکس نقطه پایان (offset)
    
    منطق:
      - از قله به سمت راست حرکت می‌کند.
      - برای wave_dir=1: تا جایی که سیگنال کاهشی است ادامه می‌دهد.
      - برای wave_dir=-1: تا جایی که سیگنال افزایشی است ادامه می‌دهد.
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


def _find_events_and_plot(
    df_signal: pd.DataFrame,        # خروجی _extract_ecg_signal
    output_dir: Path,               # پوشه ذخیره نمودار
    required_events: list[str]      # ['End Diastol', 'End Sistol', 'LVOT']
) -> dict[str, int]:
    """
    تشخیص قله‌های ECG و تعیین فریم‌های متناظر با رویدادهای درخواستی.
    
    مراحل:
      ۱) هموارسازی سیگنال با Savitzky-Golay
      ۲) تشخیص قله‌های R
      ۳) برای هر قله R: پیدا کردن Q, S, P, T و onset/offset آنها
      ۴) انتخاب آخرین چرخه کامل برای هر رویداد
      ۵) رسم و ذخیره نمودار ECG
    
    ورودی:
        df_signal     : DataFrame سیگنال استخراج‌شده
        output_dir    : مسیر ذخیره نمودار ecg_plot.png
        required_events: لیست رویدادهای لازم
    
    خروجی:
        dict: {'End Diastol': 60, 'End Sistol': 87}  (شماره فریم‌ها)
    """
    # اعتبارسنجی سیگنال
    if df_signal.empty or len(df_signal) <= 15:
        raise ValueError("استخراج سیگنال ECG با شکست مواجه شد.")

    # هموارسازی سیگنال با فیلتر Savitzky-Golay
    # (حذف نویز با حفظ شکل موج)
    df_signal["Smoothed_Signal"] = savgol_filter(
        df_signal["Signal_Value"],
        window_length=SAVGOL_WINDOW,     # 5
        polyorder=SAVGOL_POLYORDER       # 2
    )
    signal = df_signal["Smoothed_Signal"].values   # آرایه numpy از سیگنال هموارشده

    # ----- تشخیص قله‌های R -----
    r_peaks, _ = find_peaks(
        signal,
        prominence=R_PEAK_PROMINENCE,   # 15
        distance=R_PEAK_DISTANCE        # 50
    )
    # r_peaks = [45, 98, 152, 205, ...]  (ایندکس نمونه‌ها، نه شماره فریم)

    # لیست‌های ذخیره نقاط کلیدی
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
        max_idx = max(indices)                              # آخرین ایندکس
        return int(df_signal["Frame_Number"].iloc[max_idx]) # شماره فریم واقعی

    # End Diastol  = شروع موج P  (بیشترین حجم بطن)
    frame_end_diastol = get_frame(p_starts)
    # frame_end_diastol = 60  (برای dd.avi)

    # LVOT = انتهای موج S  (باز شدن دریچه آئورت)
    frame_lvot = get_frame(s_ends)
    # frame_lvot = 45  (برای ssss.avi)

    # End Sistol = انتهای موج T  (کمترین حجم بطن)
    frame_end_sistol = get_frame(t_ends)
    # frame_end_sistol = 87  (برای dd.avi)

    # fallback: فریم میانی ویدیو (اگر هیچ رویدادی پیدا نشد)
    fallback = int(df_signal["Frame_Number"].iloc[len(df_signal) // 2])

    # ----- ساخت دیکشنری خروجی -----
    event_frames = {}
    for event_name in required_events:
        if event_name == "End Diastol":
            event_frames[event_name] = frame_end_diastol or fallback
            # event_frames['End Diastol'] = 60
        elif event_name == "LVOT":
            event_frames[event_name] = frame_lvot or fallback
            # event_frames['LVOT'] = 45
        elif event_name == "End Sistol":
            event_frames[event_name] = frame_end_sistol or fallback
            # event_frames['End Sistol'] = 87
        else:
            event_frames[event_name] = fallback

    # ========================================================================
    # رسم و ذخیره نمودار ECG
    # ========================================================================
    plt.figure(figsize=(18, 8))

    # سیگنال اصلی
    plt.plot(df_signal["Sample_Index"], signal, color="black", linewidth=1)

    # قله‌ها
    plt.plot(r_peaks, signal[r_peaks], "ro", label="R")     # دایره قرمز
    plt.plot(q_peaks, signal[q_peaks], "yo", label="Q")     # دایره زرد
    plt.plot(s_peaks, signal[s_peaks], "go", label="S")     # دایره سبز
    plt.plot(p_peaks, signal[p_peaks], "bo", label="P")     # دایره آبی
    plt.plot(t_peaks, signal[t_peaks], "mo", label="T")     # دایره بنفش

    # onset/offset ها
    if p_starts:
        plt.plot(p_starts, signal[p_starts], "b>", label="P Start (End Diastol)")
    if q_starts:
        plt.plot(q_starts, signal[q_starts], "y>", label="Q Start")
    if s_ends:
        plt.plot(s_ends, signal[s_ends], "g<", label="S End (LVOT)")
    if t_ends:
        plt.plot(t_ends, signal[t_ends], "m<", label="T End (End Sistol)")

    plt.title("ECG Morphology Details")
    plt.xlabel("Sample Index")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.legend()
    plt.savefig(str(output_dir / "ecg_plot.png"), dpi=300)   # ذخیره با کیفیت ۳۰۰
    plt.close()

    return event_frames
    # خروجی برای dd.avi:
    #   {'End Diastol': 60, 'End Sistol': 87}
    # خروجی برای ssss.avi:
    #   {'End Diastol': 32, 'End Sistol': 58, 'LVOT': 45}


def _save_event_images(
    video_path: Path,                # مسیر ویدیو
    output_dir: Path,                # پوشه خروجی
    event_frames: dict[str, int]     # {'End Diastol': 60, 'End Sistol': 87}
) -> dict[str, str]:
    """
    استخراج و ذخیره فریم‌های مربوط به رویدادها از ویدیو.
    
    مراحل:
      ۱) گروه‌بندی رویدادها بر اساس شماره فریم (چند رویداد ممکن است یک فریم باشند)
      ۲) پیمایش ویدیو تا رسیدن به فریم‌های مورد نظر
      ۳) crop کردن هر فریم و ذخیره آن
    
    ورودی:
        video_path  : مسیر ویدیو
        output_dir  : پوشه ذخیره فریم‌ها
        event_frames: دیکشنری {نام رویداد: شماره فریم}
    
    خروجی:
        dict: {نام رویداد: مسیر مطلق فایل ذخیره‌شده}
        {'End Diastol': 'C:\\Users\\...\\End_Diastol\\frame_0060.jpg', ...}
    """
    # گروه‌بندی: هر شماره فریم → لیست رویدادهای آن
    # target_frames = {60: ['End Diastol'], 87: ['End Sistol']}
    target_frames = {}
    for ev_name, f_num in event_frames.items():
        if f_num not in target_frames:
            target_frames[f_num] = []
        target_frames[f_num].append(ev_name)

    max_frame_needed = max(event_frames.values()) if event_frames else 0  # 87

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {}

    current_frame = 1      # شمارنده فریم (از ۱ شروع می‌شود)
    saved_paths = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # اگر فریم فعلی یکی از فریم‌های هدف باشد
        if current_frame in target_frames:
            cropped_frame = crop_echo_frame(frame)      # حذف حاشیه‌ها
            for event_name in target_frames[current_frame]:
                # ساخت پوشه: .../events/End_Diastol/
                event_dir = output_dir / event_name.replace(" ", "_")
                event_dir.mkdir(parents=True, exist_ok=True)

                # ذخیره فریم: frame_0060.jpg
                img_path = event_dir / f"frame_{current_frame:04d}.jpg"
                cv2.imwrite(str(img_path), cropped_frame)
                saved_paths[event_name] = str(img_path.resolve())
                # saved_paths['End Diastol'] = 'C:\\Users\\...\\frame_0060.jpg'

        if current_frame >= max_frame_needed:
            break

        current_frame += 1

    cap.release()
    return saved_paths


def extract_events(
    video_path: str | Path,           # 'C:\\Users\\...\\dd.avi'
    output_dir: str | Path,           # 'C:\\Users\\...\\internal\\events'
    required_events: list[str]        # ['End Diastol', 'End Sistol']
) -> dict:
    """
    تابع اصلی استخراج رویدادهای ECG.
    
    مراحل:
      ۱) استخراج سیگنال ECG از ویدیو
      ۲) تحلیل سیگنال و یافتن فریم‌های رویدادها
      ۳) استخراج و ذخیره فریم‌های مربوطه
      ۴) تولید CSV رویدادها
    
    ورودی:
        video_path     : مسیر فایل ویدیو
        output_dir     : پوشه ذخیره خروجی‌ها
        required_events: لیست رویدادهای مورد نیاز
    
    خروجی:
        dict = {
            "total_frames": 102,
            "event_frames": {'End Diastol': 60, 'End Sistol': 87},
            "saved_frames": {
                'End Diastol': 'C:\\Users\\...\\frame_0060.jpg',
                'End Sistol': 'C:\\Users\\...\\frame_0087.jpg'
            },
            "events_csv": 'C:\\Users\\...\\event_frames.csv'
        }
    """
    # نرمال‌سازی مسیرها
    resolved_video = Path(video_path).expanduser().resolve()
    resolved_output = Path(output_dir).expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)

    # 1. استخراج سیگنال از فریم‌ها
    df_signal = _extract_ecg_signal(resolved_video)
    # df_signal: DataFrame با ستون‌های Sample_Index, Frame_Number, Signal_Value

    # 2. پیدا کردن فریم‌های حساس و تولید نمودار
    event_frames = _find_events_and_plot(df_signal, resolved_output, required_events)
    # event_frames = {'End Diastol': 60, 'End Sistol': 87}

    # 3. بریدن و ذخیره فریم‌های استخراج شده
    saved_frames = _save_event_images(resolved_video, resolved_output, event_frames)
    # saved_frames = {
    #     'End Diastol': 'C:\\Users\\...\\frame_0060.jpg',
    #     'End Sistol': 'C:\\Users\\...\\frame_0087.jpg'
    # }

    # 4. تولید CSV نهایی برای پایپ‌لاین
    # event_rows = [{'event_name': 'End Diastol', 'frame_number': 60},
    #               {'event_name': 'End Sistol', 'frame_number': 87}]
    event_rows = [{"event_name": k, "frame_number": v} for k, v in event_frames.items()]
    events_csv_path = resolved_output / "event_frames.csv"
    pd.DataFrame(event_rows).to_csv(events_csv_path, index=False)

    return {
        "total_frames": int(df_signal["Frame_Number"].max()) if not df_signal.empty else 0,
        # 102 (برای dd.avi)
        "event_frames": event_frames,
        # {'End Diastol': 60, 'End Sistol': 87}
        "saved_frames": saved_frames,
        # {'End Diastol': 'C:\\...\\frame_0060.jpg', ...}
        "events_csv": str(events_csv_path),
        # 'C:\\Users\\...\\event_frames.csv'
    }
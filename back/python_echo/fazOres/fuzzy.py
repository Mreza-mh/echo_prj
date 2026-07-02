"""
ارزیابی فازی سلامت قلب بر اساس پارامترهای اکوکاردیوگرافی.

جریان کلی:
  ۱) aggregate_patient_rows_for_fuzzy: ردیف‌های خروجی pipeline را به دیکشنری
     پارامترهای بیمار تبدیل می‌کند (تبدیل واحد cm → mm برای پارامترهای خطی).
  ۲) evaluate_patient: با منطق فازی (skfuzzy) یک امتیاز ریسک ۰ تا ۱۰۰ و
     دسته‌بندی Normal / Mild / Severe تولید می‌کند.
"""

import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# ==============================================================================
# ۱. دیکشنری تنظیمات (PARAM_CONFIG)
# ==============================================================================
# هر پارامتر فیزیولوژیک قلب یک تنظیمات دارد:
#   - male / female: (n_min, n_max, mild_max, sev_max) ← بازه‌ها به تفکیک جنسیت
#   - needs_bsa: آیا مقدار باید بر BSA (سطح بدن) تقسیم شود؟
#
# n_min    = حداقل نرمال
# n_max    = حداکثر نرمال (اگر val ≤ n_max → NORMAL)
# mild_max = آستانه Mild  (اگر n_max < val ≤ mild_max → MILD)
# sev_max  = آستانه Severe (اگر mild_max < val → SEVERE)
#
# این مقادیر بر اساس گایدلاین‌های استاندارد اکوکاردیوگرافی (ASE/EACVI) تعیین شده‌اند.

PARAM_CONFIG = {
    # --- آئورت ---
    'aortic_root': {'male': (20, 37, 42, 50), 'female': (20, 33, 38, 45), 'needs_bsa': False},
    # ریشه آئورت (mm): نرمال ≤37, Mild ≤42, Severe >42
    'aortic_asc':  {'male': (22, 38, 43, 55), 'female': (20, 35, 40, 50), 'needs_bsa': False},
    # آئورت صعودی (mm): نرمال ≤38, Mild ≤43, Severe >43

    # --- دهلیزها (نیاز به نرمال‌سازی با BSA) ---
    'la_volume':   {'male': (16, 34, 41, 50), 'female': (16, 34, 41, 50), 'needs_bsa': True},
    # حجم دهلیز چپ (mL/m²): نرمال ≤34, Mild ≤41, Severe >41
    'ra_volume':   {'male': (25, 39, 46, 60), 'female': (21, 33, 40, 55), 'needs_bsa': True},
    # حجم دهلیز راست (mL/m²): نرمال ≤39, Mild ≤46, Severe >46

    # --- بطن راست ---
    'rv_diameter': {'male': (20, 41, 46, 55), 'female': (20, 41, 46, 55), 'needs_bsa': False},
    # قطر بطن راست (mm): نرمال ≤41, Mild ≤46, Severe >46
    'rv_wall':     {'male': (1, 5, 7, 10), 'female': (1, 5, 7, 10), 'needs_bsa': False},
    # ضخامت دیواره بطن راست (mm): نرمال ≤5, Mild ≤7, Severe >7

    # --- بطن چپ (نیاز به نرمال‌سازی با BSA) ---
    'lv_edv':      {'male': (35, 74, 89, 110), 'female': (35, 61, 73, 90), 'needs_bsa': True},
    # حجم پایان دیاستولی بطن چپ (mL/m²): نرمال ≤74, Mild ≤89, Severe >89
    'lv_esv':      {'male': (15, 31, 39, 55), 'female': (15, 24, 32, 45), 'needs_bsa': True},
    # حجم پایان سیستولی بطن چپ (mL/m²): نرمال ≤31, Mild ≤39, Severe >39

    # --- ضخامت دیواره‌ها ---
    'ivs_thickness': {'male': (6, 10, 13, 17), 'female': (6, 9, 12, 16), 'needs_bsa': False},
    # ضخامت سپتوم بین بطنی (mm): نرمال ≤10, Mild ≤13, Severe >13
    'pw_thickness':  {'male': (6, 10, 13, 17), 'female': (6, 9, 12, 16), 'needs_bsa': False},
    # ضخامت دیواره خلفی (mm): نرمال ≤10, Mild ≤13, Severe >13

    # --- قطر بطن چپ ---
    'lv_diameter': {'male': (42, 58, 64, 75), 'female': (38, 52, 58, 65), 'needs_bsa': False},
    # قطر داخلی بطن چپ (mm): نرمال ≤58, Mild ≤64, Severe >64

    # --- شریان ریوی ---
    'pa_diameter': {'male': (15, 25, 30, 40), 'female': (15, 25, 30, 40), 'needs_bsa': False},
    # قطر شریان ریوی (mm): نرمال ≤25, Mild ≤30, Severe >30
}

# نگاشت نام اندازه‌گیری pipeline → نام پارامتر PARAM_CONFIG
_PIPELINE_PARAM_MAP = {
    "aortic_root":       "aortic_root",
    "aorta":             "aortic_asc",
    "ivs":               "ivs_thickness",
    "lvpw":              "pw_thickness",
    "lvid":              "lv_diameter",
    "left_atrium_area":  "la_volume",
    "right_atrium_area": "ra_volume",
    "lv_area":           "lv_edv",
}

# پارامترهای خطی که pipeline بر حسب cm می‌دهد ولی PARAM_CONFIG بر حسب mm است
_LINEAR_PARAMS_CM = {"aortic_root", "aortic_asc", "ivs_thickness", "pw_thickness", "lv_diameter"}


def _as_float(value: Any) -> float | None:
    """تبدیل امن به float؛ برای None / NaN / inf / مقدار غیرعددی، None برمی‌گرداند."""
    if value is None:
        return None
    try:
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
    except Exception:
        return None


def aggregate_patient_rows_for_fuzzy(
    rows: list[dict[str, Any]],
    patient_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    ساخت دیکشنری آماده ارزیابی فازی از ردیف‌های خلاصه pipeline.
    توسط pipeline.results.aggregate_and_evaluate_fuzzy صدا زده می‌شه (قبل از evaluate_patient).

    ورودی:
        rows          : ردیف‌های pipeline_summary (هر ردیف یک اندازه‌گیری/رویداد)
        patient_config: اطلاعات پایه بیمار (gender, weight, height, ...) — کپی می‌شود

    خروجی:
        {
            "aggregated_data": دیکشنری پارامترها برای evaluate_patient,
            "processed_views": لیست نماهای پردازش‌شده (مثلاً ["a4c", "plax"]),
            "rows_used":       تعداد ردیف‌های معتبر استفاده‌شده,
        }
    """
    base = dict(patient_config or {})
    processed_views: list[str] = []
    rows_used = 0

    # روی تک‌تک ردیف‌های همه‌ی ویدیوها/رویدادها پیمایش می‌کنه و مقادیر معتبر رو در base جمع می‌کنه
    for row in rows:
        # فقط ردیف‌های موفق (ok/partial) یا بدون وضعیت
        if row.get("measurement_status") not in (None, "ok", "partial"):
            continue
        rows_used += 1

        view_name = row.get("detected_view")
        if view_name and view_name not in processed_views:
            processed_views.append(str(view_name))

        # اندازه‌گیری خطی این ردیف (cm) → نگاشت به پارامتر فازی
        mapped_key = _PIPELINE_PARAM_MAP.get(str(row.get("measurement_name")))
        measurement_cm = _as_float(row.get("length_cm"))
        if mapped_key and measurement_cm is not None:
            if mapped_key in _LINEAR_PARAMS_CM:
                base[mapped_key] = measurement_cm * 10.0    # cm → mm
            else:
                base[mapped_key] = measurement_cm

        # مساحت‌های دهلیزی و بطنی (cm²) — اگر در ردیف موجود باشند
        la_area = _as_float(row.get("a4c_left_atrium_area_cm2"))
        if la_area is not None:
            base["la_volume"] = la_area
        ra_area = _as_float(row.get("a4c_right_atrium_area_cm2"))
        if ra_area is not None:
            base["ra_volume"] = ra_area
        lv_area = _as_float(row.get("lv_area_cm2"))
        if lv_area is not None:
            base["lv_edv"] = lv_area

    return {
        "aggregated_data": base,
        "processed_views": processed_views,
        "rows_used": rows_used,
    }


# ==============================================================================
# ۲. توابع اصلی
# ==============================================================================

def calculate_bsa(weight_kg, height_cm):
    """
    محاسبه سطح بدن (Body Surface Area) با فرمول Mosteller.

    فرمول: BSA = sqrt((W × H) / 3600)

    مثال: وزن 10 و قد 160 → sqrt(1600 / 3600) = 0.667 m²

    چرا BSA مهم است؟
      - حجم‌های قلبی (la_volume, ra_volume, lv_edv, lv_esv) باید نسبت به اندازه بدن
        نرمال‌سازی شوند: فرد بزرگ‌جثه قلب بزرگتری دارد، پس حجم‌ها بر BSA تقسیم می‌شوند.

    خروجی:
        float به متر مربع، یا None اگر وزن/قد موجود نباشد
    """
    if weight_kg and height_cm:
        return math.sqrt((weight_kg * height_cm) / 3600.0)
    return None


def evaluate_patient(patient_data, patient_name="Patient", show_plot=False):
    """
    ارزیابی فازی سلامت قلب بیمار بر اساس پارامترهای اکوکاردیوگرافی.
    ورودی این تابع خروجی aggregate_patient_rows_for_fuzzy (aggregated_data) است.

    مراحل:
      ۱) تعیین جنسیت و محاسبه BSA
      ۲) برای هر پارامتر موجود در patient_data:
           - اگر needs_bsa=True باشد، مقدار بر BSA تقسیم می‌شود
           - توابع عضویت فازی (Normal, Mild, Severe) تعریف می‌شود
      ۳) ساخت ۳ قانون:
           - Normal Rule: همه پارامترها Normal باشند (AND)
           - Mild Rule:   حداقل یکی Mild باشد (OR)
           - Severe Rule: حداقل یکی Severe باشد (OR)
      ۴) محاسبه خروجی فازی با روش MOM (Mean of Maximum)
      ۵) رسم نمودارهای تحلیلی (در صورت درخواست)

    ورودی:
        patient_data: دیکشنری مقادیر بیمار، مثلاً:
            {'gender': 'male', 'weight': 10, 'height': 160,
             'la_volume': 21.25, 'ra_volume': 11.07, 'lv_edv': 34.64, 'ivs_thickness': 0.84}
            نکته: کلیدهای «<param>_processed» (مقدار بعد از تقسیم بر BSA) به همین
            دیکشنری اضافه می‌شوند و در fuzzy_summary.json هم ذخیره خواهند شد.
        patient_name: نام بیمار برای عنوان نمودارها
        show_plot   : اگر Path یا رشته باشد، نمودارها در آن پوشه ذخیره می‌شوند؛
                      اگر True باشد، نمودارها نمایش داده می‌شوند

    خروجی:
        {"score": 0.0, "category": "Normal", "reasons": [],
         "text": "Score: 0.0/100 | Category: Normal\\nReasons:\\n  - All normal."}
        یا در صورت خطا: {"error": "...", "traceback": "..."}
    """
    # ========================================================================
    # قدم ۱: استخراج اطلاعات پایه و محاسبه BSA
    # ========================================================================
    # تبدیل gender از عدد به string (MongoDB: 1=زن, 2=مرد یا 0=زن, 1=مرد)
    gender_raw = patient_data.get('gender', patient_data.get('sex', 'male'))
    if isinstance(gender_raw, (int, float)):
        gender = 'male' if int(gender_raw) in (1, 2) else 'female'
    elif isinstance(gender_raw, str):
        gender = 'male' if gender_raw.lower() in ('male', 'مرد', 'm', '1', '2') else 'female'
    else:
        gender = 'male'  # پیش‌فرض

    bsa = calculate_bsa(patient_data.get('weight'), patient_data.get('height'))

    # ========================================================================
    # قدم ۲: تعریف خروجی فازی (Risk)
    # ========================================================================
    # risk: متغیر خروجی از ۰ تا ۱۰۰
    #   - Normal [0, 0, 40]  : مثلثی با قله در ۰
    #   - Mild   [20, 50, 80]: مثلثی با قله در ۵۰
    #   - Severe [60, 100, 100]: مثلثی با قله در ۱۰۰
    #
    # defuzzify_method='mom': Mean of Maximum
    #   - مرکز ناحیه‌ای که بیشترین درجه عضویت را دارد
    #   - حالت همه-نرمال: ناحیه Normal فعال → score ≈ 0
    #   - اگر Severe فعال باشد: ناحیه [60, 100] → score ≈ 80
    risk = ctrl.Consequent(np.arange(0, 101, 1), 'risk')
    risk['Normal'] = fuzz.trimf(risk.universe, [0, 0, 40])
    risk['Mild']   = fuzz.trimf(risk.universe, [20, 50, 80])
    risk['Severe'] = fuzz.trimf(risk.universe, [60, 100, 100])
    risk.defuzzify_method = 'mom'

    # ========================================================================
    # قدم ۳: پردازش هر پارامتر (BSA normalization + تعریف توابع عضویت)
    # ========================================================================
    fuzzy_inputs = {}  # {param_name: Antecedent}

    for param, config in PARAM_CONFIG.items():
        if param not in patient_data:
            continue

        val = patient_data[param]      # مقدار خام از اندازه‌گیری

        # ----- نرمال‌سازی با BSA (برای حجم‌ها) -----
        if config['needs_bsa']:
            if not bsa:
                continue               # بدون BSA این پارامتر قابل ارزیابی نیست
            val = val / bsa            # مثلاً la_volume = 21.25 / 0.667 = 31.88

        # ----- بازه‌های جنسیت -----
        n_min, n_max, mild_max, sev_max = config[gender]
        # مثلاً la_volume (male): n_min=16, n_max=34, mild_max=41, sev_max=50

        # ----- تعریف جهان (universe) این پارامتر: از ۰ تا max_universe با گام ۰.۱ -----
        # به اندازه‌ای بزرگ که هم مقدار بیمار و هم ناحیه Severe را پوشش دهد
        max_universe = max(val + 10, sev_max + 20)
        antecedent = ctrl.Antecedent(np.arange(0, max_universe, 0.1), param)

        # ----- توابع عضویت (مثال‌ها برای la_volume male) -----
        # Normal: ذوزنقه [0, 0, n_max, mild_max] — تا n_max عضویت ۱، سپس کاهش خطی تا mild_max
        #   مثال: trapmf [0, 0, 34, 41]
        antecedent['Normal'] = fuzz.trapmf(antecedent.universe, [0, 0, n_max, mild_max])

        # Mild: مثلث [n_max, mild_max, sev_max] — قله در mild_max
        #   مثال: trimf [34, 41, 50]
        antecedent['Mild'] = fuzz.trimf(antecedent.universe, [n_max, mild_max, sev_max])

        # Severe: ذوزنقه [mild_max, sev_max, max, max] — از sev_max به بعد عضویت ۱
        #   مثال: trapmf [41, 50, 70, 70]
        antecedent['Severe'] = fuzz.trapmf(antecedent.universe, [mild_max, sev_max, max_universe, max_universe])

        fuzzy_inputs[param] = antecedent
        # مقدار پردازش‌شده روی patient_data ذخیره می‌شود (عمداً — در fuzzy_summary.json هم می‌رود)
        patient_data[param + '_processed'] = val

    if not fuzzy_inputs:
        return {"error": "No valid parameters provided."}

    # ========================================================================
    # قدم ۴: ساخت قوانین فازی
    # ========================================================================
    #   - Normal Rule: همه پارامترها Normal باشند (AND)
    #   - Mild Rule:   حداقل یکی Mild باشد (OR)
    #   - Severe Rule: حداقل یکی Severe باشد (OR)
    severe_condition, mild_condition, normal_condition = None, None, None
    for antecedent in fuzzy_inputs.values():
        if severe_condition is None:
            severe_condition = antecedent['Severe']
            mild_condition   = antecedent['Mild']
            normal_condition = antecedent['Normal']
        else:
            severe_condition = severe_condition | antecedent['Severe']   # OR
            mild_condition   = mild_condition | antecedent['Mild']       # OR
            normal_condition = normal_condition & antecedent['Normal']   # AND

    rules = [
        ctrl.Rule(normal_condition, risk['Normal']),
        ctrl.Rule(mild_condition, risk['Mild']),
        ctrl.Rule(severe_condition, risk['Severe']),
    ]

    risk_ctrl = ctrl.ControlSystem(rules)
    risk_sim = ctrl.ControlSystemSimulation(risk_ctrl)

    # ========================================================================
    # قدم ۵: اعمال مقادیر بیمار به شبیه‌سازی
    # ========================================================================
    for param in fuzzy_inputs:
        risk_sim.input[param] = patient_data[param + '_processed']

    # ========================================================================
    # قدم ۶: محاسبه و تفسیر نتیجه
    # ========================================================================
    try:
        risk_sim.compute()
        score = risk_sim.output['risk']
        # حالت همه-نرمال: فقط Normal Rule فعال → MOM روی ناحیه Normal → score = 0.0

        category = "Normal" if score < 35 else "Mild" if score < 65 else "Severe"

        # ----- محاسبه درجات عضویت هر پارامتر (برای گزارش و نمودار) -----
        reasons = []
        overall_norm_deg = 1.0   # AND: با ۱ شروع، با min کاهش می‌یابد
        overall_mild_deg = 0.0   # OR: با ۰ شروع، با max افزایش می‌یابد
        overall_sev_deg  = 0.0   # OR: با ۰ شروع، با max افزایش می‌یابد
        param_degrees = {}       # {param: (val, norm_deg, mild_deg, sev_deg)} برای رسم نمودار

        for param, antecedent in fuzzy_inputs.items():
            val = patient_data[param + '_processed']

            # درجه عضویت مقدار بیمار در هر سه مجموعه
            norm_deg = fuzz.interp_membership(antecedent.universe, antecedent['Normal'].mf, val)
            mild_deg = fuzz.interp_membership(antecedent.universe, antecedent['Mild'].mf, val)
            sev_deg  = fuzz.interp_membership(antecedent.universe, antecedent['Severe'].mf, val)
            # مثلاً la_volume=31.88 ≤ n_max=34 → در ناحیه flat ذوزنقه → Normal=1.0

            param_degrees[param] = (val, norm_deg, mild_deg, sev_deg)

            overall_norm_deg = min(overall_norm_deg, norm_deg)   # AND
            overall_mild_deg = max(overall_mild_deg, mild_deg)   # OR
            overall_sev_deg  = max(overall_sev_deg, sev_deg)     # OR

            # تشخیص دلیل ریسک: مجموعه‌ای که بیشترین عضویت را دارد
            if sev_deg >= mild_deg and sev_deg >= norm_deg and sev_deg > 0:
                reasons.append(f"{param} is SEVERE ({val:.1f})")
            elif mild_deg > norm_deg and mild_deg > 0:
                reasons.append(f"{param} is MILD ({val:.1f})")

        reasons_text = "\n  - ".join(reasons) if reasons else "All normal."

        # ----- رسم نمودارهای تحلیلی -----
        if show_plot:
            save_dir = Path(show_plot) if isinstance(show_plot, (str, Path)) else None
            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)
            _plot_inputs_fuzzification(fuzzy_inputs, param_degrees, patient_name, save_dir)
            _plot_rule_aggregation(
                risk, overall_norm_deg, overall_mild_deg, overall_sev_deg,
                score, category, patient_name, save_dir,
            )

        return {
            "score": float(score),
            "category": category,
            "reasons": reasons,
            "text": f"Score: {score:.1f}/100 | Category: {category}\nReasons:\n  - {reasons_text}",
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


# ==============================================================================
# ۳. مصورسازی (نمودارها)
# ==============================================================================

def _plot_inputs_fuzzification(fuzzy_inputs, param_degrees, patient_name, save_dir):
    """
    نمودار ۱: Fuzzification ورودی‌ها — برای هر پارامتر یک subplot:
      - منحنی‌های Normal (سبز)، Mild (نارنجی)، Severe (قرمز)
      - خط عمودی سیاه: مقدار بیمار
      - نقاط رنگی: درجه عضویت در هر مجموعه

    اگر save_dir داده شود، تصویر ذخیره می‌شود؛ وگرنه نمایش داده می‌شود.
    """
    num_inputs = len(fuzzy_inputs)
    cols = 3
    rows = math.ceil(num_inputs / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
    fig.suptitle(f"Patient Inputs Fuzzification: {patient_name}", fontsize=16, fontweight='bold')

    axes = axes.flatten() if isinstance(axes, np.ndarray) else [axes]

    for idx, (param, antecedent) in enumerate(fuzzy_inputs.items()):
        ax = axes[idx]
        val, n_deg, m_deg, s_deg = param_degrees[param]
        x = antecedent.universe

        # توابع عضویت
        ax.plot(x, antecedent['Normal'].mf, 'g', label='Normal')
        ax.plot(x, antecedent['Mild'].mf, 'orange', label='Mild')
        ax.plot(x, antecedent['Severe'].mf, 'r', label='Severe')

        # خط عمودی مقدار بیمار
        ax.vlines(val, 0, 1, color='black', linestyle='--', linewidth=2, label=f'Patient Val: {val:.1f}')

        # نقاط تقاطع (درجه عضویت)
        if n_deg > 0: ax.plot(val, n_deg, 'go', markersize=6)
        if m_deg > 0: ax.plot(val, m_deg, 'o', color='orange', markersize=6)
        if s_deg > 0: ax.plot(val, s_deg, 'ro', markersize=6)

        ax.set_title(f"{param}\nN:{n_deg:.2f} | M:{m_deg:.2f} | S:{s_deg:.2f}", fontsize=10)
        ax.set_ylim([0, 1.05])
        ax.grid(True, linestyle=':', alpha=0.6)
        if idx == 0: ax.legend()

    # پاک کردن subplotهای خالی
    for i in range(num_inputs, len(axes)):
        fig.delaxes(axes[i])

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save_dir:
        fig.savefig(save_dir / f"{patient_name}_1_inputs.png")
        plt.close(fig)
    else:
        plt.show()


def _plot_rule_aggregation(
    risk, norm_deg, mild_deg, sev_deg,
    score, category, patient_name, save_dir,
):
    """
    نمودار ۲: تجمیع قوانین و خروجی نهایی — نشان می‌دهد هر قانون چقدر فعال شده
    و امتیاز نهایی چگونه دی‌فازی شده است.

    اگر save_dir داده شود، تصویر ذخیره می‌شود؛ وگرنه نمایش داده می‌شود.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    x_risk = risk.universe                     # [0, 1, ..., 100]
    mf_norm = risk['Normal'].mf
    mf_mild = risk['Mild'].mf
    mf_sev  = risk['Severe'].mf

    # برش توابع خروجی بر اساس درجه فعال‌سازی قوانین
    norm_activation = np.fmin(norm_deg, mf_norm)
    mild_activation = np.fmin(mild_deg, mf_mild)
    sev_activation  = np.fmin(sev_deg, mf_sev)

    # تجمیع نهایی (OR روی خروجی قوانین)
    aggregated = np.fmax(norm_activation, np.fmax(mild_activation, sev_activation))

    # توابع پایه (خط‌چین)
    ax.plot(x_risk, mf_norm, 'g--', alpha=0.5, label='Normal Rule Base')
    ax.plot(x_risk, mf_mild, 'orange', linestyle='--', alpha=0.5, label='Mild Rule Base')
    ax.plot(x_risk, mf_sev, 'r--', alpha=0.5, label='Severe Rule Base')

    # نواحی فعال‌شده (پر شده)
    ax.fill_between(x_risk, 0, norm_activation, color='g', alpha=0.3,
                    label=f'Norm Activation ({norm_deg:.2f})')
    ax.fill_between(x_risk, 0, mild_activation, color='orange', alpha=0.3,
                    label=f'Mild Activation ({mild_deg:.2f})')
    ax.fill_between(x_risk, 0, sev_activation, color='r', alpha=0.3,
                    label=f'Sev Activation ({sev_deg:.2f})')

    # خط تجمیع (آبی ضخیم) و خط عمودی مقدار دی‌فازی‌شده
    ax.plot(x_risk, aggregated, 'b', linewidth=3, label='Aggregated Output')
    ax.vlines(score, 0, max(np.max(aggregated), 0.1), color='black', linestyle='-', linewidth=2,
              label=f'Final Defuzzified Score: {score:.1f}')

    ax.set_title(f"Rule Evaluation & Aggregation ({patient_name})\nFinal Category: {category}", fontweight='bold')
    ax.set_xlabel("Risk Score $0 \\dots 100$")
    ax.set_ylabel("Degree of Membership")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1.05)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()

    if save_dir:
        fig.savefig(save_dir / f"{patient_name}_2_output_aggregation.png")
        plt.close(fig)
    else:
        plt.show()


# اجرای تستی کد در صورت نیاز
if __name__ == "__main__":
    test_patient = {
        'gender': 'male', 'weight': 80, 'height': 180,
        'lv_edv': 120,       # کمی بالا (نرمال ≤74)
        'rv_diameter': 48    # کمی بالا (نرمال ≤41)
    }
    result = evaluate_patient(test_patient, "Test_Patient", show_plot=True)
    print(result['text'])

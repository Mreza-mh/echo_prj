import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import math
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Any

# ==========================================
# 1. Configuration Dictionary (PARAM_CONFIG)
# ==========================================
# هر پارامتر فیزیولوژیک قلب یک تنظیمات دارد:
#   - male: (n_min, n_max, mild_max, sev_max) ← بازه‌های نرمال، Mild، Severe برای مردان
#   - female: (...) ← بازه‌های زنان
#   - needs_bsa: آیا مقدار باید بر BSA (سطح بدن) تقسیم شود؟
#
# n_min  = حداقل نرمال
# n_max  = حداکثر نرمال (اگر val ≤ n_max → NORMAL)
# mild_max = آستانه Mild (اگر n_max < val ≤ mild_max → MILD)
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


def aggregate_patient_rows_for_fuzzy(
    rows: list[dict[str, Any]],
    patient_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build fuzzy-ready patient data from pipeline summary rows."""
    base = dict(patient_config or {})
    processed_views: list[str] = []
    debug_rows_used = 0

    param_map = {
        "aortic_root": "aortic_root",
        "aorta": "aortic_asc",
        "ivs": "ivs_thickness",
        "lvpw": "pw_thickness",
        "lvid": "lv_diameter",
        "left_atrium_area": "la_volume",
        "right_atrium_area": "ra_volume",
        "lv_area": "lv_edv",
    }
    linear_params_cm = {"aortic_root", "aortic_asc", "ivs_thickness", "pw_thickness", "lv_diameter"}

    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
            if math.isnan(parsed) or math.isinf(parsed):
                return None
            return parsed
        except Exception:
            return None

    for row in rows:
        if row.get("measurement_status") not in (None, "ok", "partial"):
            continue
        debug_rows_used += 1

        view_name = row.get("detected_view")
        if view_name and view_name not in processed_views:
            processed_views.append(str(view_name))

        measurement_name = row.get("measurement_name")
        mapped_key = param_map.get(str(measurement_name))
        measurement_cm = _as_float(row.get("length_cm"))
        if mapped_key and measurement_cm is not None:
            if mapped_key in linear_params_cm:
                base[mapped_key] = measurement_cm * 10.0
            else:
                base[mapped_key] = measurement_cm

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
        "rows_used": debug_rows_used,
    }

# ==========================================
# 2. Functions
# ==========================================

def calculate_bsa(weight_kg, height_cm):
    """
    محاسبه سطح بدن (Body Surface Area) با فرمول Mosteller.
    
    فرمول: BSA = sqrt((W × H) / 3600)
    
    ورودی:
        weight_kg: وزن به کیلوگرم (مثلاً 10)
        height_cm: قد به سانتی‌متر (مثلاً 160)
    
    خروجی:
        float: مساحت سطح بدن به متر مربع
    
    مثال از لاگ واقعی:
        BSA = sqrt((10 × 160) / 3600) = sqrt(1600 / 3600) = sqrt(0.4444) = 0.6667 m²
    
    چرا BSA مهم است؟
      - حجم‌های قلبی (la_volume, ra_volume, lv_edv, lv_esv) باید نسبت به اندازه بدن نرمال‌سازی شوند.
      - یک فرد بزرگ‌جثه قلب بزرگتری دارد، پس حجم‌ها باید بر BSA تقسیم شوند.
      - در این بیمار: وزن ۱۰ کیلو و قد ۱۶۰ سانتی‌متر → BSA = 0.667 (فرد لاغر/کوچک)
        پس حجم‌های اندازه‌گیری‌شده بعد از تقسیم بر BSA بزرگتر می‌شوند
        (مثلاً la_volume: 21.25 / 0.667 = 31.88)
    """
    if weight_kg and height_cm:
        return math.sqrt((weight_kg * height_cm) / 3600.0)
    return None


def evaluate_patient(patient_data, patient_name="Patient", show_plot=False):
    """
    ارزیابی فازی سلامت قلب بیمار بر اساس پارامترهای اکوکاردیوگرافی.
    
    مراحل:
      ۱) تعیین جنسیت و محاسبه BSA
      ۲) برای هر پارامتر موجود در patient_data:
           - اگر needs_bsa=True باشد، مقدار را بر BSA تقسیم می‌کند
           - توابع عضویت فازی (Normal, Mild, Severe) تعریف می‌شود
      ۳) ساخت ۳ قانون:
           - Normal Rule: همه پارامترها باید Normal باشند (AND)
           - Mild Rule:   حداقل یکی Mild باشد → ریسک Mild (OR)
           - Severe Rule: حداقل یکی Severe باشد → ریسک Severe (OR)
      ۴) محاسبه خروجی فازی با روش MOM (Mean of Maximum)
      ۵) رسم نمودارهای تحلیلی (در صورت درخواست)
    
    ورودی:
        patient_data: دیکشنری مقادیر بیمار
            از لاگ واقعی: {
                'gender': 'male', 'weight': 10, 'height': 160,
                'id': '404445623',
                'la_volume': 21.252873001124748,
                'ra_volume': 11.066555821800577,
                'lv_edv': 34.63983568878674,
                'ivs_thickness': 0.8371042930537949
            }
        patient_name: نام بیمار برای عنوان نمودارها
        show_plot   : اگر Path یا رشته باشد، نمودارها را در آن پوشه ذخیره می‌کند
                     اگر True باشد، نمودارها را نمایش می‌دهد
    
    خروجی (از لاگ واقعی):
        {
            "score": 0.0,
            "category": "Normal",
            "reasons": [],
            "text": "Score: 0.0/100 | Category: Normal\nReasons:\n  - All normal."
        }
    """
    # ========================================================================
    # قدم ۱: استخراج اطلاعات پایه و محاسبه BSA
    # ========================================================================
    gender = patient_data.get('gender', 'male')  # 'male'
    weight = patient_data.get('weight')           # 10
    height = patient_data.get('height')           # 160
    bsa = calculate_bsa(weight, height)
    # bsa = 0.6666666666666666
    
    fuzzy_inputs = {}  # دیکشنری ورودی‌های فازی: {param_name: Antecedent}

    # ========================================================================
    # قدم ۲: تعریف خروجی فازی (Risk)
    # ========================================================================
    # risk: متغیر خروجی از ۰ تا ۱۰۰
    #   - Normal [0, 0, 40]: مثلثی با قله در ۰، انتها در ۴۰
    #   - Mild   [20, 50, 80]: مثلثی با قله در ۵۰
    #   - Severe [60, 100, 100]: مثلثی با قله در ۱۰۰
    #
    # defuzzify_method='mom': Mean of Maximum
    #   - مرکز ناحیه‌ای که بیشترین درجه عضویت را دارد
    #   - برای حالت Normal: ناحیه [0, 20] فعال → مرکز ≈ 10 → score ≈ 0
    #   - اگر Severe هم فعال باشد: ناحیه [60, 100] → مرکز ≈ 80 → score ≈ 80
    
    risk = ctrl.Consequent(np.arange(0, 101, 1), 'risk')
    risk['Normal'] = fuzz.trimf(risk.universe, [0, 0, 40])
    risk['Mild'] = fuzz.trimf(risk.universe, [20, 50, 80])
    risk['Severe'] = fuzz.trimf(risk.universe, [60, 100, 100])
    risk.defuzzify_method = 'mom'

    # ========================================================================
    # قدم ۳: پردازش هر پارامتر (BSA normalization + تعریف توابع عضویت)
    # ========================================================================
    for param, config in PARAM_CONFIG.items():
        if param in patient_data:
            val = patient_data[param]      # مقدار خام از اندازه‌گیری
            raw_val = val                  # نگه‌داشتن مقدار اولیه برای لاگ
            
            # ----- نرمال‌سازی با BSA (برای حجم‌ها) -----
            if config['needs_bsa']:
                if bsa:
                    val = val / bsa
                    # مثال از لاگ: la_volume = 21.2529 / 0.6667 = 31.8793
                    #            ra_volume = 11.0666 / 0.6667 = 16.5998
                    #            lv_edv    = 34.6398 / 0.6667 = 51.9598
                else:
                    continue  # اگر BSA محاسبه نشد، این پارامتر را رد کن
            
            # ----- بازه‌های جنسیت -----
            ranges = config[gender]
            n_min, n_max, mild_max, sev_max = ranges
            # مثلاً برای la_volume (male): n_min=16, n_max=34, mild_max=41, sev_max=50
            
            # ----- تعیین وضعیت -----
            # (این فقط برای لاگ است، منطق فازی خودش درجه عضویت را محاسبه می‌کند)
            if val <= n_max:
                status = "NORMAL"      # val ≤ 34 → NORMAL
            elif val <= mild_max:
                status = "MILD"        # 34 < val ≤ 41 → MILD
            else:
                status = "SEVERE"      # val > 41 → SEVERE
            
            # از لاگ: la_volume=31.88, n_max=34 → 31.88 ≤ 34 → NORMAL
            #         ra_volume=16.60, n_max=39 → 16.60 ≤ 39 → NORMAL
            #         lv_edv=51.96, n_max=74   → 51.96 ≤ 74 → NORMAL
            #         ivs_thickness=0.837, n_max=10 → 0.837 ≤ 10 → NORMAL
            
            # ----- تعریف جهان (universe) برای این پارامتر -----
            max_universe = max(val + 10, sev_max + 20)
            # universe از ۰ تا max_universe با گام ۰.۱
            # مثلاً برای la_volume: max(31.88+10, 50+20) = max(41.88, 70) = 70
            
            # ----- تعریف توابع عضویت -----
            antecedent = ctrl.Antecedent(np.arange(0, max_universe, 0.1), param)
            
            # Normal: trapmf [0, 0, n_max, mild_max]
            #   - ذوزنقه‌ای: از ۰ تا n_max کاملاً Normal (عضویت ۱)
            #   - از n_max تا mild_max خطی کاهش می‌یابد
            #   - بعد از mild_max عضویت صفر
            #   مثال la_volume: trapmf [0, 0, 34, 41]
            antecedent['Normal'] = fuzz.trapmf(antecedent.universe, [0, 0, n_max, mild_max])
            
            # Mild: trimf [n_max, mild_max, sev_max]
            #   - مثلثی: قله در mild_max
            #   - از n_max شروع، در mild_max به ۱ می‌رسد، در sev_max به ۰
            #   مثال la_volume: trimf [34, 41, 50]
            antecedent['Mild'] = fuzz.trimf(antecedent.universe, [n_max, mild_max, sev_max])
            
            # Severe: trapmf [mild_max, sev_max, max_universe, max_universe]
            #   - ذوزنقه‌ای: از mild_max شروع، در sev_max کاملاً Severe (عضویت ۱)
            #   - تا max_universe ادامه دارد
            #   مثال la_volume: trapmf [41, 50, 70, 70]
            antecedent['Severe'] = fuzz.trapmf(antecedent.universe, [mild_max, sev_max, max_universe, max_universe])
            
            fuzzy_inputs[param] = antecedent
            patient_data[param + '_processed'] = val  # ذخیره مقدار پردازش‌شده

    # از لاگ: fuzzy_inputs شامل ۴ پارامتر:
    #   la_volume: processed_value = 31.8793
    #   ra_volume: processed_value = 16.5998
    #   lv_edv:    processed_value = 51.9598
    #   ivs_thickness: processed_value = 0.8371

    if not fuzzy_inputs:
        return {"error": "No valid parameters provided."}

    # ========================================================================
    # قدم ۴: ساخت قوانین فازی
    # ========================================================================
    # منطق:
    #   - Normal Rule: همه پارامترها Normal باشند (AND)
    #   - Mild Rule:   حداقل یکی Mild باشد (OR)
    #   - Severe Rule: حداقل یکی Severe باشد (OR)
    #
    # اولویت: Severe > Mild > Normal
    # (اگر هم Severe و هم Mild فعال باشند، Severe برنده است چون MOM روی هر دو اعمال می‌شود)
    
    severe_condition, mild_condition, normal_condition = None, None, None
    for param_name, antecedent in fuzzy_inputs.items():
        if severe_condition is None:
            severe_condition = antecedent['Severe']
            mild_condition = antecedent['Mild']
            normal_condition = antecedent['Normal']
        else:
            # Severe: OR (حداقل یکی Severe)
            severe_condition = severe_condition | antecedent['Severe']
            # Mild: OR (حداقل یکی Mild)
            mild_condition = mild_condition | antecedent['Mild']
            # Normal: AND (همه باید Normal باشند)
            normal_condition = normal_condition & antecedent['Normal']

    rules = [
        ctrl.Rule(normal_condition, risk['Normal']),
        ctrl.Rule(mild_condition, risk['Mild']),
        ctrl.Rule(severe_condition, risk['Severe'])
    ]

    risk_ctrl = ctrl.ControlSystem(rules)
    risk_sim = ctrl.ControlSystemSimulation(risk_ctrl)

    # ========================================================================
    # قدم ۵: اعمال مقادیر بیمار به شبیه‌سازی
    # ========================================================================
    for param in fuzzy_inputs.keys():
        risk_sim.input[param] = patient_data[param + '_processed']
        # risk_sim.input['la_volume'] = 31.8793
        # risk_sim.input['ra_volume'] = 16.5998
        # risk_sim.input['lv_edv'] = 51.9598
        # risk_sim.input['ivs_thickness'] = 0.8371

    # ========================================================================
    # قدم ۶: محاسبه و تفسیر نتیجه
    # ========================================================================
    try:
        risk_sim.compute()
        score = risk_sim.output['risk']
        # score = 0.0 (از لاگ)
        # چرا صفر؟ چون همه پارامترها Normal هستند:
        #   - Normal Rule با درجه ۱.۰ فعال می‌شود
        #   - Mild Rule با درجه ۰.۰ فعال می‌شود
        #   - Severe Rule با درجه ۰.۰ فعال می‌شود
        #   - MOM روی ناحیه Normal [0, 40] → مرکز ≈ 0
        
        category = "Normal" if score < 35 else "Mild" if score < 65 else "Severe"
        # category = "Normal" (چون 0.0 < 35)

        # ====================================================================
        # محاسبه درجات عضویت (برای گزارش و نمودار)
        # ====================================================================
        reasons = []
        overall_norm_deg = 1.0   # AND: با ۱ شروع، با min کاهش می‌یابد
        overall_mild_deg = 0.0   # OR: با ۰ شروع، با max افزایش می‌یابد
        overall_sev_deg = 0.0    # OR: با ۰ شروع، با max افزایش می‌یابد
        
        param_degrees = {}  # برای رسم نمودار

        for param, antecedent in fuzzy_inputs.items():
            val = patient_data[param + '_processed']
            
            # درجه عضویت در هر مجموعه
            norm_deg = fuzz.interp_membership(antecedent.universe, antecedent['Normal'].mf, val)
            mild_deg = fuzz.interp_membership(antecedent.universe, antecedent['Mild'].mf, val)
            sev_deg = fuzz.interp_membership(antecedent.universe, antecedent['Severe'].mf, val)
            
            # از لاگ (همه نرمال):
            #   la_volume=31.88:     Normal=1.0000, Mild=0.0000, Severe=0.0000
            #   ra_volume=16.60:     Normal=1.0000, Mild=0.0000, Severe=0.0000
            #   lv_edv=51.96:        Normal=1.0000, Mild=0.0000, Severe=0.0000
            #   ivs_thickness=0.837: Normal=1.0000, Mild=0.0000, Severe=0.0000
            #
            # چرا همه Normal=1.0؟
            #   - la_volume=31.88 ≤ n_max=34 → در ناحیه flat ذوزنقه Normal
            #   - ra_volume=16.60 ≤ n_max=39 → در ناحیه flat ذوزنقه Normal
            #   - lv_edv=51.96 ≤ n_max=74 → در ناحیه flat ذوزنقه Normal
            #   - ivs_thickness=0.837 ≤ n_max=10 → در ناحیه flat ذوزنقه Normal
            
            param_degrees[param] = (val, norm_deg, mild_deg, sev_deg)

            # به‌روزرسانی کلی
            overall_norm_deg = min(overall_norm_deg, norm_deg)   # AND
            overall_mild_deg = max(overall_mild_deg, mild_deg)   # OR
            overall_sev_deg = max(overall_sev_deg, sev_deg)      # OR

            # تشخیص دلیل ریسک
            if sev_deg >= mild_deg and sev_deg >= norm_deg and sev_deg > 0:
                reasons.append(f"{param} is SEVERE ({val:.1f})")
            elif mild_deg > norm_deg and mild_deg > 0:
                reasons.append(f"{param} is MILD ({val:.1f})")

        # از لاگ:
        #   overall_norm_deg = min(1.0, 1.0, 1.0, 1.0) = 1.0
        #   overall_mild_deg = max(0.0, 0.0, 0.0, 0.0) = 0.0
        #   overall_sev_deg  = max(0.0, 0.0, 0.0, 0.0) = 0.0
        #   reasons = [] (همه نرمال)

        reasons_text = "\n  - ".join(reasons) if reasons else "All normal."

        # ====================================================================
        # ۴. رسم نمودارهای تحلیلی کامل
        # ====================================================================
        if show_plot:
            save_dir = Path(show_plot) if isinstance(show_plot, (str, Path)) else None
            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)

            # --- نمودار ۱: Fuzzification ورودی‌ها ---
            # برای هر پارامتر یک subplot رسم می‌کند:
            #   - منحنی‌های Normal (سبز)، Mild (نارنجی)، Severe (قرمز)
            #   - خط عمودی سیاه: مقدار بیمار
            #   - نقاط رنگی: درجه عضویت در هر مجموعه
            num_inputs = len(fuzzy_inputs)
            cols = 3
            rows = math.ceil(num_inputs / cols)
            fig1, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
            fig1.suptitle(f"Patient Inputs Fuzzification: {patient_name}", fontsize=16, fontweight='bold')
            
            if isinstance(axes, np.ndarray):
                axes = axes.flatten()
            else:
                axes = [axes]

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
                fig1.delaxes(axes[i])
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            if save_dir:
                fig1.savefig(save_dir / f"{patient_name}_1_inputs.png")
                plt.close(fig1)
            else:
                plt.show()

            # --- نمودار ۲: تجمیع قوانین و خروجی نهایی ---
            # نمایش می‌دهد که هر قانون چقدر فعال شده و خروجی نهایی چگونه محاسبه شده
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            x_risk = risk.universe  # [0, 1, 2, ..., 100]
            mf_r_norm = risk['Normal'].mf
            mf_r_mild = risk['Mild'].mf
            mf_r_sev = risk['Severe'].mf

            # برش توابع خروجی بر اساس درجه فعال‌سازی قوانین
            norm_activation = np.fmin(overall_norm_deg, mf_r_norm)
            mild_activation = np.fmin(overall_mild_deg, mf_r_mild)
            sev_activation  = np.fmin(overall_sev_deg, mf_r_sev)
            # از لاگ: norm_activation = min(1.0, Normal MF) → Normal MF
            #         mild_activation = min(0.0, Mild MF) → صفر
            #         sev_activation  = min(0.0, Severe MF) → صفر
            
            # تجمیع نهایی (OR روی خروجی قوانین)
            aggregated = np.fmax(norm_activation, np.fmax(mild_activation, sev_activation))
            # از لاگ: aggregated = Normal MF (چون فقط Normal فعال است)

            # رسم توابع پایه (خط‌چین)
            ax2.plot(x_risk, mf_r_norm, 'g--', alpha=0.5, label='Normal Rule Base')
            ax2.plot(x_risk, mf_r_mild, 'orange', linestyle='--', alpha=0.5, label='Mild Rule Base')
            ax2.plot(x_risk, mf_r_sev, 'r--', alpha=0.5, label='Severe Rule Base')
            
            # رسم نواحی فعال‌شده (پر شده)
            ax2.fill_between(x_risk, 0, norm_activation, color='g', alpha=0.3,
                           label=f'Norm Activation ({overall_norm_deg:.2f})')
            ax2.fill_between(x_risk, 0, mild_activation, color='orange', alpha=0.3,
                           label=f'Mild Activation ({overall_mild_deg:.2f})')
            ax2.fill_between(x_risk, 0, sev_activation, color='r', alpha=0.3,
                           label=f'Sev Activation ({overall_sev_deg:.2f})')
            
            # خط تجمیع (آبی ضخیم)
            ax2.plot(x_risk, aggregated, 'b', linewidth=3, label='Aggregated Output')
            
            # خط عمودی سیاه: مقدار دی‌فازی شده
            ax2.vlines(score, 0, max(np.max(aggregated), 0.1), color='black', linestyle='-', linewidth=2, 
                      label=f'Final Defuzzified Score: {score:.1f}')

            ax2.set_title(f"Rule Evaluation & Aggregation ({patient_name})\nFinal Category: {category}", fontweight='bold')
            ax2.set_xlabel("Risk Score $0 \\dots 100$")
            ax2.set_ylabel("Degree of Membership")
            ax2.set_xlim(0, 100)
            ax2.set_ylim(0, 1.05)
            ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
            ax2.grid(True, linestyle=':', alpha=0.6)
            plt.tight_layout()
            
            if save_dir:
                fig2.savefig(save_dir / f"{patient_name}_2_output_aggregation.png")
                plt.close(fig2)
            else:
                plt.show()

        # ====================================================================
        # بازگشت نتیجه
        # ====================================================================
        return {
            "score": float(score),           # 0.0
            "category": category,            # "Normal"
            "reasons": reasons,              # [] (همه نرمال)
            "text": f"Score: {score:.1f}/100 | Category: {category}\nReasons:\n  - {reasons_text}"
            # "Score: 0.0/100 | Category: Normal\nReasons:\n  - All normal."
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


# اجرای تستی کد در صورت نیاز
if __name__ == "__main__":
    test_patient = {
        'gender': 'male', 'weight': 80, 'height': 180,
        'lv_edv': 120,       # کمی بالا (نرمال ≤74)
        'rv_diameter': 48    # کمی بالا (نرمال ≤41)
    }
    result = evaluate_patient(test_patient, "Test_Patient", show_plot=True)
    print(result['text'])
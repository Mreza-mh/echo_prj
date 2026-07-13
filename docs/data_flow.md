# مسیر داده در پایپ‌لاین اکو (Data Flow)

این سند نشان می‌دهد داده از ویدیو تا نمایش در فرانت چه مسیری طی می‌کند،
هر خروجی کجا ذخیره می‌شود، و به LLM دقیقاً چه چیزی داده می‌شود.

نقطه‌ی شروع: `back/python_echo/main.py`

---

## نمای کلی

```
پوشه‌ی ویدیوهای بیمار
        │
        ├─► [۰] MongoDB: اطلاعات بیمار خوانده می‌شود  (get_patient_config)
        │
        ├─► [۱] دو مدل ML روی اطلاعات بیمار           (run_ml_analysis → ml_result)
        │
        ├─► [۲] پردازش هر ویدیو (تشخیص ویو، اندازه‌گیری)  (process_video → rows)
        │
        ├─► [۳] جمع‌بندی فازی روی همه‌ی rowها          (aggregate_and_evaluate_fuzzy → fuzzy_result)
        │
        └─► [۴] گزارش نهایی: ML + فازی + LLM           (generate_and_save_final_report)
```

سه منبع تحلیلی مستقل داریم که در گام [۴] کنار هم می‌آیند:
| منبع | از کجا | چه می‌دهد |
|---|---|---|
| **دو مدل ML** | اطلاعات دموگرافیک بیمار (سن، فشار، کلسترول، BMI...) | امتیاز ریسک قلبی-عروقی + عوامل خطر |
| **فازی (Fuzzy)** | اندازه‌گیری‌های اکو از ویدیوها | امتیاز + دسته‌بندی + دلایل ساختاری قلب |
| **LLM** | خروجی دو منبع بالا | متن فارسی قابل‌فهم برای بیمار |

---

## گام ۱ — خروجی دو مدل ML

**کد:** `ai_service/ml_predictor.py` → `MLRiskPredictor.predict()`

دو مدل جدا اجرا می‌شوند و ترکیب می‌شوند:
- **HD** (Heart Disease): بر اساس شاخص‌های بالینی مثل ECG/تست ورزش
- **CV** (Cardiovascular): بر اساس فشار خون / کلسترول / سبک زندگی

خروجی `ml_result` این ساختار را دارد:
```python
{
  "hd_result":      {...},   # نتیجه‌ی تفصیلی مدل HD (احتمال، درصد، confidence)
  "cv_result":      {...},   # نتیجه‌ی تفصیلی مدل CV
  "combined_score": 62.5,    # امتیاز ترکیبی دو مدل (۰ تا ۱۰۰)
  "severity":       "MODERATE",
  "risk_factors":   [...],   # عوامل خطر بالینی شناسایی‌شده
  "confidence":     0.71,
  "bmi":            27.3,
}
```

### ⚠️ خروجی دو مدل کجا ذخیره می‌شود؟

**هیچ‌جا به‌صورت مستقل ذخیره نمی‌شود** — نه فایل `ml_result.json` جدا، نه entry جدا در MongoDB.

`ml_result` فقط در حافظه می‌ماند و مستقیم به گام ۴ پاس داده می‌شود. آنجا داخل
`_build_final_report_data` مصرف می‌شود و فقط **عصاره‌اش** وارد `final_report.json` می‌شود:
- `risk_factors` → به‌طور کامل
- `combined_score` و `severity` → **بعد از میانگین/ترکیب با نتیجه‌ی فازی**

یعنی `hd_result` و `cv_result` تفصیلی (درصد جداگانه‌ی هر مدل) در هیچ فایلی و در فرانت **دیده نمی‌شوند**.

---

## گام ۲ — پردازش هر ویدیو

**کد:** `pipeline/processing.py` → `process_video()` (یک‌بار به‌ازای هر فایل ویدیو)

مراحل: تشخیص ویو (`plax`/`a4c`) → استخراج رویداد (End Diastol/Sistol/LVOT) →
محاسبه‌ی مقیاس → اندازه‌گیری با مدل‌های YOLO → (فقط a4c) محاسبه‌ی حجم دهلیز/بطن.

خروجی: لیستی از **rows** (سطر اندازه‌گیری). هر row دو نسخه دارد:
- `internal_row` — همه‌ی فیلدها (مسیر داخلی، پیکسل، دیباگ)
- `public_row` — زیرمجموعه‌ی امن برای فرانت

### ذخیره‌سازی (تابع `save_reports`)

روی دیسک، زیر `<patient_id>/<visit_date>/<view>/`:
| فایل | نسخه | برای چه؟ |
|---|---|---|
| `reports/result.json` | public | چیزی که فرانت مستقیم مصرف می‌کند |
| `reports/measurements.csv` | public | جدول اندازه‌گیری‌ها |
| `internal/reports/run_report.json` | internal | نسخه‌ی کامل برای دیباگ |
| `internal/reports/measurement_results_full.csv` | internal | CSV کامل داخلی |

در MongoDB: یک **entry per-view** (دارای `view_instance`، بدون `type`) شامل
`measurements`, `a4c_volume`, `lv_volume`, `classification`, `files`.

---

## گام ۳ — خروجی فازی (Fuzzy)

**کد:** `pipeline/results.py` → `aggregate_and_evaluate_fuzzy()` (یک‌بار برای کل ویزیت)

همه‌ی rowهای همه‌ی ویدیوها → یک دیکشنری `aggregated_data` → موتور فازی
(`fazOres/fuzzy.py`) اجرا می‌شود.

خروجی `fuzzy_result`:
```python
{
  "score":    58.0,        # امتیاز ریسک ساختاری قلب (۰ تا ۱۰۰)
  "category": "Mild",      # Normal / Mild / Severe
  "reasons":  [...],       # یافته‌های غیرطبیعی، مثل "ivs_thickness is SEVERE"
}
```

### خروجی فازی کجا ذخیره می‌شود؟

روی دیسک، زیر `<patient_id>/<visit_date>/summary_<views>_<HH_MM>/`:
| فایل | برای چه؟ |
|---|---|
| `reports/fuzzy_summary.json` | خروجی کامل فازی + `aggregated_data` + نمودارها |
| `media/summary/*.png` | نمودارهای تحلیل فازی |

در MongoDB: یک entry با `type = "fuzzy_summary"` شامل:
- `result` → همان `fuzzy_result` (score/category/reasons) + مسیر نمودارها (`plots`)
- `aggregated_data` → داده‌ی تجمیعیِ ورودی فازی (فرانت برای مدل سه‌بعدی قلب ازش می‌خواند)

---

## گام ۴ — گزارش نهایی + LLM

**کد:** `pipeline/results.py` → `generate_and_save_final_report()` (آخر کار)

اینجا سه منبع کنار هم می‌آیند: `ml_result` + `fuzzy_result` + `all_rows`

1. `_build_final_report_data(...)` همه را در یک دیکشنری تمیز ترکیب می‌کند
2. این دیکشنری در `final_report/final_report.json` ذخیره می‌شود
3. همین دیکشنری به LLM داده می‌شود → متن فارسی
4. متن در `llm_patient_report.txt` + entry مونگو (`type = "llm_final_report"`)

### به LLM دقیقاً چه چیزی می‌دهیم؟

**کد:** `pipeline/llm_report_generator.py` → `_build_prompt()`

فقط این فیلدهای `final_report_data` وارد پرامپت می‌شوند:
```
بیمار: 58 ساله، مرد
امتیاز ریسک: 62.5 از ۱۰۰ (متوسط)      ← ترکیب ML + فازی
نتیجه اکو: خفیف                         ← از فازی (category)
یافته‌های اکو:                          ← از فازی (reasons، ترجمه‌شده به فارسی)
- ضخامت دیواره بین بطنی به طور قابل توجهی بزرگتر از حد طبیعی
عوامل خطر بالینی:                       ← از ML (risk_factors)
- فشار خون بالا
- سیگاری
```

قوانین لحن/فرمت (فارسی، ساده، ۳-۴ پاراگراف) در `_SYSTEM_PROMPT` هستند، نه در این پرامپت.

**به LLM داده نمی‌شود:** درصد تفکیکی هر مدل (`hd_result`/`cv_result`)، `confidence`،
و اندازه‌گیری‌های عددی خام اکو.

---

## ساختار سند MongoDB

هر بیمار **یک سند** دارد. هر ویزیت یک آرایه است که چند نوع entry قاطی هم دارد:

```jsonc
{
  "_id": "2",
  "patient_info": { ... },
  "last_updated": "...",
  "visits": {
    "2026-07-06": [
      { "view_instance": "a4c", "measurements": [...], "a4c_volume": {...} },  // per-view
      { "view_instance": "plax", "measurements": [...] },                       // per-view
      { "type": "fuzzy_summary",    "result": {...}, "aggregated_data": {...} },
      { "type": "llm_final_report", "report_text": "..." }
    ]
  }
}
```

فرانت با `visit.type` بین این‌ها تفکیک می‌کند.

---

## در فرانت چه چیزهایی نمایش داده می‌شوند؟

**کامپوننت‌ها:** داشبورد کاربر (`user-dashboard`) و پنل دکتر (`echo-history`) — هر دو
یک ساختار مشابه دارند.

| بخش UI | از کدام entry / فیلد | توضیح |
|---|---|---|
| **مدل سه‌بعدی قلب** | `fuzzy_summary.aggregated_data` + `result.score` | اندازه‌ها روی مدل GLB قلب |
| **کارت خلاصه تشخیصی** | `fuzzy_summary.result` | امتیاز، دسته‌بندی، دلایل + نمودارهای فازی |
| **کارت متن هوش مصنوعی** | `llm_final_report.report_text` | متن فارسی گزارش (همان خروجی LLM) |
| **جدول اندازه‌گیری‌ها** | per-view `measurements` | مقادیر + تصاویر فریم/اندازه‌گیری |
| **گالری تصاویر تحلیلی** | per-view `files` / `a4c_volume` / `lv_volume` | ECG، تشخیص مقیاس، سگمنتیشن دهلیز/بطن |

### آنچه در فرانت دیده نمی‌شود
- درصد تفکیکی دو مدل ML (`hd_result`/`cv_result`) — فقط امتیاز ترکیبی در دل گزارش LLM.
- فایل‌های internal (`run_report.json`, CSVهای کامل) — فقط برای دیباگ.

---

## خلاصه‌ی «هر ذخیره‌سازی برای چیست»

| خروجی | محل | مصرف‌کننده |
|---|---|---|
| `result.json` (per-view) | دیسک public + مونگو | فرانت: جدول + گالری |
| `run_report.json` (per-view) | دیسک internal | دیباگ |
| `fuzzy_summary.json` | دیسک + مونگو (`fuzzy_summary`) | فرانت: خلاصه + مدل سه‌بعدی |
| `final_report.json` | دیسک | آرشیو/دیباگ + ورودی LLM |
| `llm_patient_report.txt` | دیسک + مونگو (`llm_final_report`) | فرانت: کارت متن AI |
| `ml_result` | **فقط حافظه** | عصاره‌اش → `final_report.json` |

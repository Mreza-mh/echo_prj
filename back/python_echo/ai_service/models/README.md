# ML Models Directory

این پوشه شامل مدل‌های یادگیری ماشین برای پیش‌بینی ریسک بیماری‌های قلبی و عروقی است.

## فایل‌های مورد نیاز

### مدل‌های اصلی:
1. **Heart Disease Model (HD)**
   - `hd_logisticregression.pkl` یا `hd_logisticregression.joblib`
   - مدل Logistic Regression برای پیش‌بینی بیماری قلبی
   - ورودی: داده‌های ECG، تست ورزش، علائم بالینی

2. **Cardiovascular Model (CV)**
   - `cv_catboost.pkl` یا `cv_catboost.joblib`
   - مدل CatBoost برای پیش‌بینی بیماری‌های قلبی-عروقی
   - ورودی: فشار خون، BMI، سبک زندگی

3. **Scaler**
   - `hd_scaler.pkl` یا `hd_scaler.joblib`
   - StandardScaler برای نرمال‌سازی ورودی مدل HD

### فایل‌های کمکی (اختیاری):
- `hd_features.json` - لیست فیچرهای مدل HD
- `cv_features.json` - لیست فیچرهای مدل CV

## فرمت‌های پشتیبانی شده

کد به صورت خودکار هر دو فرمت را پشتیبانی می‌کند:
- `.pkl` - فرمت Pickle استاندارد Python
- `.joblib` - فرمت بهینه‌شده Joblib

## ساختار فایل‌ها

```
models/
├── hd_logisticregression.pkl    # مدل HD
├── cv_catboost.pkl              # مدل CV
├── hd_scaler.pkl                # Scaler
├── hd_features.json             # لیست فیچرها (اختیاری)
├── cv_features.json             # لیست فیچرها (اختیاری)
└── README.md                    # این فایل
```

## نحوه استفاده

```python
from ai_service.ml_predictor import MLRiskPredictor

# ایجاد predictor (خودکار مدل‌ها را بارگذاری می‌کند)
predictor = MLRiskPredictor()

# پیش‌بینی ریسک
patient_data = {
    "age": 55,
    "gender": 1,
    "height": 172,
    "weight": 90,
    "ap_hi": 158,
    "ap_lo": 98,
    # ... سایر فیلدها
}

result = predictor.predict(patient_data)
print(f"امتیاز ریسک: {result['combined_score']}%")
print(f"شدت: {result['severity']}")
```

## تست مدل‌ها

برای تست بارگذاری و عملکرد مدل‌ها:

```bash
cd back/python_echo
python test_ml_predictor.py
```

## Feature Engineering

مدل‌ها به صورت خودکار فیچرهای زیر را محاسبه می‌کنند:

### HD Model Features:
- `bp_category` - دسته‌بندی فشار خون
- `rate_pressure_product` - حاصل‌ضرب ضربان و فشار
- `chronotropic_index` - شاخص کرونوتروپیک
- `st_depression_index` - شاخص افسردگی ST
- `age_st_depression` - تعامل سن و ST

### CV Model Features:
- `bmi` - شاخص توده بدنی
- `bmi_category` - دسته‌بندی BMI
- `map` - میانگین فشار شریانی
- `pulse_pressure` - فشار نبض
- `hypertension_grade` - درجه فشار خون بالا
- `metabolic_risk_score` - امتیاز ریسک متابولیک
- `lifestyle_risk_score` - امتیاز ریسک سبک زندگی
- `age_bmi_interaction` - تعامل سن و BMI
- `age_hypertension_interaction` - تعامل سن و فشار خون

## Missing Value Handling

اگر برخی فیلدها موجود نباشند:
1. از میانه‌های بالینی استفاده می‌شود
2. confidence score کاهش می‌یابد
3. پیش‌بینی همچنان انجام می‌شود

## خروجی

```json
{
  "combined_score": 65.3,
  "combined_prob": 0.653,
  "severity": "MODERATE",
  "confidence": 0.85,
  "bmi": 30.4,
  "risk_factors": [
    {
      "feature": "age",
      "value": 65,
      "label_fa": "سن بالا (بیش از ۶۵ سال)",
      "label_en": "Age > 65 years"
    }
  ],
  "hd_result": {
    "model": "HD_LogisticRegression",
    "probability_pct": 68.5,
    "confidence": 0.88
  },
  "cv_result": {
    "model": "CV_CatBoost",
    "probability_pct": 62.1,
    "confidence": 0.82
  }
}
```

## نکات مهم

1. **فرمت فایل**: کد هر دو فرمت `.pkl` و `.joblib` را پشتیبانی می‌کند
2. **Missing Values**: تمام فیلدها اختیاری هستند
3. **Feature Engineering**: به صورت خودکار انجام می‌شود
4. **Confidence**: نشان‌دهنده کیفیت داده‌های ورودی است
5. **Risk Factors**: عوامل خطر به صورت خودکار شناسایی می‌شوند

## عیب‌یابی

### مدل بارگذاری نمی‌شود:
```bash
# بررسی وجود فایل‌ها
ls -la models/

# تست بارگذاری
python test_ml_predictor.py
```

### خطای فرمت:
- مطمئن شوید فایل‌ها با `joblib.dump()` یا `pickle.dump()` ذخیره شده‌اند
- نسخه Python و scikit-learn باید سازگار باشد

### خطای Feature:
- بررسی کنید `hd_features.json` و `cv_features.json` وجود دارند
- ترتیب فیچرها باید دقیقاً مطابق زمان training باشد

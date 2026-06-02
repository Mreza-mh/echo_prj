# سیستم تولید گزارش هوشمند برای بیمار

این سیستم با استفاده از هوش مصنوعی (Arvan Cloud AI)، گزارش‌های اکوکاردیوگرافی را به زبان ساده و قابل فهم برای بیماران تبدیل می‌کند.

## ویژگی‌ها

✅ **تولید خودکار گزارش**: پس از پردازش اکو و فازی، گزارش دوستانه تولید می‌شود  
✅ **صرفه‌جویی در توکن**: فقط اطلاعات خلاصه به LLM ارسال می‌شود  
✅ **گزارش HTML زیبا**: یک صفحه HTML کامل با طراحی مدرن تولید می‌شود  
✅ **ذخیره در MongoDB**: دسترسی آسان از API لاراول  
✅ **قابل سفارشی‌سازی**: پرامپت‌ها و template را می‌توانید تغییر دهید  

---

## نصب و راه‌اندازی

### 1. نصب کتابخانه‌های مورد نیاز

```bash
cd back/python_echo
pip install -r requirements.txt
```

### 2. تنظیم API Key در `.env`

فایل `back/python_echo/.env` را باز کنید و API Key خود را وارد کنید:

```env
# Arvan Cloud AI Configuration
ARVAN_AI_API_KEY=your_api_key_here
ARVAN_AI_BASE_URL=https://api.arvancloud.ir/llm/v1/chat/completions
ARVAN_AI_MODEL=gpt-4o-mini
```

**نکته**: همان API Key که در لاراول استفاده کردید را اینجا هم بگذارید.

---

## نحوه استفاده

### روش 1: اجرای خودکار (توصیه می‌شود)

هنگامی که `main.py` را اجرا می‌کنید، گزارش LLM به صورت خودکار تولید می‌شود:

```bash
python main.py /path/to/patient/folder
```

خروجی:
```
📋 تولید گزارش نهایی...
   ✓ ریسک نهایی : ✅ نرمال (امتیاز: 2.9/100)
   ...
🤖 تولید گزارش هوشمند برای بیمار...
   ✓ گزارش LLM تولید شد
   ✓ HTML: 2/2026-06-02/final_report/patient_report.html
   ✓ Text: 2/2026-06-02/final_report/llm_patient_report.txt
```

### روش 2: استفاده مستقیم از ماژول

```python
from pipeline.llm_report_generator import LLMReportGenerator
import json

# خواندن گزارش نهایی
with open('result/2/2026-06-02/final_report/final_report.json', 'r') as f:
    final_report_data = json.load(f)

# تولید گزارش
generator = LLMReportGenerator()
report_text = generator.generate_patient_report(final_report_data)
print(report_text)

# تولید HTML
html_report = generator.generate_html_report(report_text, final_report_data)
with open('patient_report.html', 'w', encoding='utf-8') as f:
    f.write(html_report)
```

---

## دسترسی از Laravel API

### 1. دریافت لیست ویزیت‌های بیمار

```http
GET /api/patient-report/visits/{patient_id}
Authorization: Bearer {token}
```

پاسخ:
```json
{
  "success": true,
  "patient_info": {...},
  "visits": [
    {
      "date": "2026-06-02",
      "views_count": 2,
      "has_final_report": true
    }
  ]
}
```

### 2. دریافت گزارش کامل

```http
GET /api/patient-report/report/{patient_id}/{visit_date}
Authorization: Bearer {token}
```

پاسخ شامل:
- اطلاعات بیمار
- گزارش LLM
- گزارش فازی
- اندازه‌گیری‌ها

### 3. نمایش گزارش HTML در مرورگر

```http
GET /api/patient-report/html/{patient_id}/{visit_date}
```

این route یک صفحه HTML زیبا نمایش می‌دهد (بدون نیاز به احراز هویت).

### 4. دریافت فقط متن گزارش

```http
GET /api/patient-report/text/{patient_id}/{visit_date}
Authorization: Bearer {token}
```

### 5. خلاصه وضعیت بیمار (برای داشبورد)

```http
GET /api/patient-report/summary/{patient_id}
Authorization: Bearer {token}
```

---

## ساختار فایل‌های خروجی

```
back/laravel/public/echos/
└── {patient_id}/
    └── {visit_date}/
        └── final_report/
            ├── llm_patient_report.txt   # متن خالص
            └── patient_report.html       # HTML زیبا
```

---

## سفارشی‌سازی

### تغییر پرامپت

فایل `back/python_echo/pipeline/llm_report_generator.py` را باز کنید و متد `_build_prompt` را ویرایش کنید:

```python
def _build_prompt(self, data: Dict[str, Any]) -> str:
    # پرامپت خود را اینجا بنویسید
    prompt = f"""...
    """
    return prompt
```

### تغییر طراحی HTML

متد `generate_html_report` را ویرایش کنید و CSS دلخواه را اضافه کنید.

### استفاده از مدل دیگر

در `.env` مدل را تغییر دهید:

```env
ARVAN_AI_MODEL=gpt-4o  # یا هر مدل دیگری
```

---

## عیب‌یابی

### خطا: "ARVAN_AI_API_KEY not found"

- فایل `.env` را بررسی کنید
- مطمئن شوید که `python-dotenv` نصب شده است

### خطا: "LLM failed to generate report"

- اتصال اینترنت را بررسی کنید
- API Key را در پنل Arvan Cloud بررسی کنید
- لاگ‌ها را بررسی کنید: `print(response.text)`

### گزارش تولید نمی‌شود

- مطمئن شوید که `final_report.json` وجود دارد
- مطمئن شوید که `generate_final_patient_report` در `main.py` فراخوانی می‌شود

---

## نمونه خروجی

### متن گزارش (llm_patient_report.txt):

```
با سلام و احترام،

نتایج بررسی اکوکاردیوگرافی شما نشان می‌دهد که وضعیت قلب شما 
در وضعیت نرمال قرار دارد. تمام پارامترهای اندازه‌گیری‌شده 
در محدوده طبیعی هستند.

برای حفظ سلامت قلب، توصیه می‌شود:
- ورزش منظم هوازی انجام دهید
- از رژیم غذایی سالم استفاده کنید
- استرس را کنترل کنید

پیگیری دوره‌ای هر 6 ماه توصیه می‌شود.

با آرزوی سلامتی
```

### HTML Report:

یک صفحه کامل با:
- هدر رنگی با لوگو
- کارت اطلاعات بیمار
- نمایش امتیاز ریسک به صورت دایره
- متن گزارش با فرمت زیبا
- جدول اندازه‌گیری‌ها
- Disclaimer در پایین

---

## نکات مهم

⚠️ **حفظ حریم خصوصی**: API Key را در فایل عمومی commit نکنید  
⚠️ **محدودیت توکن**: سیستم طراحی شده تا کمتر از 800 توکن مصرف کند  
⚠️ **کش کردن**: برای کاهش هزینه، می‌توانید گزارش‌ها را کش کنید  

---

## تماس و پشتیبانی

در صورت بروز مشکل:
1. لاگ‌های Python را بررسی کنید
2. لاگ‌های Laravel را بررسی کنید (`storage/logs/laravel.log`)
3. از دستور `python -m pipeline.llm_report_generator` برای تست استفاده کنید

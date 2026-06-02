"""
سیستم تولید گزارش نهایی برای بیمار با استفاده از LLM
این ماژول داده‌های پردازش‌شده را به یک متن دوستانه و قابل فهم تبدیل می‌کند.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# بارگذاری تنظیمات
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class LLMReportGenerator:
    """تولید گزارش نهایی با استفاده از Arvan Cloud AI"""
    
    def __init__(self):
        self.api_key = os.getenv("ARVAN_AI_API_KEY", "")
        self.api_base = os.getenv("ARVAN_AI_BASE_URL", "https://api.arvancloud.ir/llm/v1/chat/completions")
        self.model = os.getenv("ARVAN_AI_MODEL", "gpt-4o-mini")
        
        # بررسی اینکه آیا URL شامل API key است یا خیر
        # اگر URL شامل gateway/models باشد، یعنی API key در URL است
        self.key_in_url = "gateway/models" in self.api_base
        
        if not self.key_in_url and not self.api_key:
            raise ValueError("ARVAN_AI_API_KEY not found in .env file and URL doesn't contain embedded key")
    
    def _call_llm(self, prompt: str, max_tokens: int = 800) -> str:
        """فراخوانی API هوش مصنوعی"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": """تو یک دستیار پزشکی متخصص در قلب و عروق هستی که گزارش‌های اکوکاردیوگرافی را به زبان ساده و قابل فهم برای بیماران توضیح می‌دهی.
                        
قوانین مهم:
1. فقط به زبان فارسی پاسخ بده
2. لحن محترمانه، دلگرم‌کننده و صمیمی باشد
3. از اصطلاحات پزشکی پیچیده استفاده نکن
4. اگر همه چیز نرمال است، بیمار را آرام کن
5. اگر مشکلی وجود دارد، بدون ترساندن توضیح بده
6. توصیه‌های عملی و کاربردی ارائه بده
7. فقط متن گزارش را بنویس، بدون عنوان یا توضیحات اضافی"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": max_tokens
            }
            
            # ساخت headers بر اساس نوع URL
            headers = {"Content-Type": "application/json"}
            if not self.key_in_url and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.post(
                self.api_base,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # حذف تگ‌های <think> اگر وجود داشته باشد
                import re
                content = re.sub(r'<think>[\s\S]*?</think>', '', content)
                content = re.sub(r'<think>[\s\S]*', '', content)
                
                return content.strip()
            else:
                print(f"LLM API Error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return ""
    
    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """ساخت پرامپت برای LLM با اطلاعات خلاصه"""
        
        # استخراج اطلاعات پایه
        patient_info = data.get("patient", {})
        age = patient_info.get("age", "نامشخص")
        gender_code = patient_info.get("gender", "male")
        gender = "مرد" if gender_code in ["male", "مرد", "m", 1, 2] else "زن"
        
        # اطلاعات ارزیابی کلی
        assessment = data.get("overall_assessment", {})
        risk_score = assessment.get("risk_score", 0)
        severity = assessment.get("severity_fa", "نرمال")
        
        # اطلاعات فازی
        echo_analysis = data.get("echo_analysis", {})
        fuzzy_category = echo_analysis.get("fuzzy_category_fa", "نرمال")
        reasons = echo_analysis.get("reasons", [])
        
        # ساخت پرامپت
        prompt = f"""به یک بیمار {age} ساله {gender} که اکوکاردیوگرافی انجام داده، گزارش نتیجه را توضیح بده.

اطلاعات کلی:
- امتیاز ریسک کلی: {risk_score:.1f} از ۱۰۰
- وضعیت: {severity}
- نتیجه تحلیل اکو: {fuzzy_category}

"""
        
        if reasons and len(reasons) > 0:
            prompt += "نکات قابل توجه در بررسی:\n"
            for reason in reasons:
                # تبدیل اصطلاحات انگلیسی به فارسی
                reason_fa = self._translate_medical_term(reason)
                prompt += f"- {reason_fa}\n"
        else:
            prompt += "- تمام پارامترهای بررسی‌شده در محدوده طبیعی هستند\n"
        
        prompt += """

لطفاً یک گزارش ۳ تا ۴ پاراگرافی بنویس که شامل این موارد باشد:

۱. توضیح کلی وضعیت قلب بیمار (به زبان ساده)
۲. معنی نتایج برای سلامت بیمار
۳. توصیه‌های عملی برای نگهداری سلامت قلب
۴. آیا نیاز به پیگیری بیشتر هست یا خیر

مهم: فقط متن گزارش را بنویس، بدون عنوان یا header."""
        
        return prompt
    
    def _translate_medical_term(self, term: str) -> str:
        """تبدیل اصطلاحات پزشکی انگلیسی به فارسی"""
        translations = {
            "la_volume": "حجم دهلیز چپ",
            "ra_volume": "حجم دهلیز راست",
            "lv_edv": "حجم بطن چپ در انتهای دیاستول",
            "lv_esv": "حجم بطن چپ در انتهای سیستول",
            "ivs_thickness": "ضخامت دیواره بین بطنی",
            "pw_thickness": "ضخامت دیواره خلفی",
            "lv_diameter": "قطر بطن چپ",
            "aortic_root": "ریشه آئورت",
            "aortic_asc": "آئورت صعودی",
            "rv_diameter": "قطر بطن راست",
            "rv_wall": "دیواره بطن راست",
            "pa_diameter": "قطر شریان ریوی",
            "SEVERE": "به طور قابل توجهی بزرگتر از حد طبیعی",
            "MILD": "کمی بزرگتر از حد طبیعی",
            "NORMAL": "در محدوده طبیعی"
        }
        
        result = term
        for eng, fa in translations.items():
            result = result.replace(eng, fa)
        
        return result
    
    def generate_patient_report(self, final_report_data: Dict[str, Any]) -> str:
        """تولید گزارش نهایی برای بیمار"""
        prompt = self._build_prompt(final_report_data)
        report_text = self._call_llm(prompt)
        
        if not report_text:
            # اگر LLM پاسخ ندهد، یک متن پیش‌فرض بازگردان
            severity = final_report_data.get("overall_assessment", {}).get("severity_fa", "نرمال")
            return f"""با سلام و احترام،

نتایج بررسی اکوکاردیوگرافی شما نشان می‌دهد که وضعیت قلب شما در وضعیت {severity} قرار دارد.

لطفاً برای دریافت توضیحات کامل با پزشک معالج خود مشورت کنید.

با آرزوی سلامتی"""
        
        return report_text
    
    def generate_html_report(
        self,
        llm_report: str,
        final_report_data: Dict[str, Any],
        measurement_summary: Optional[str] = None
    ) -> str:
        """تولید گزارش HTML زیبا برای نمایش در مرورگر"""
        
        patient_info = final_report_data.get("patient", {})
        assessment = final_report_data.get("overall_assessment", {})
        echo_analysis = final_report_data.get("echo_analysis", {})
        
        # رنگ بر اساس شدت
        severity = assessment.get("severity", "NORMAL")
        color_map = {
            "NORMAL": "#27ae60",
            "LOW": "#27ae60", 
            "MODERATE": "#f39c12",
            "MILD": "#f39c12",
            "HIGH": "#e74c3c",
            "SEVERE": "#e74c3c"
        }
        severity_color = color_map.get(severity, "#95a5a6")
        
        emoji_map = {
            "NORMAL": "✅",
            "LOW": "✅",
            "MODERATE": "⚠️",
            "MILD": "⚠️", 
            "HIGH": "❌",
            "SEVERE": "❌"
        }
        severity_emoji = emoji_map.get(severity, "ℹ️")
        
        # ساخت HTML
        html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>گزارش اکوکاردیوگرافی</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.8;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border-right: 4px solid {severity_color};
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .info-row:last-child {{
            border-bottom: none;
        }}
        
        .info-label {{
            font-weight: bold;
            color: #555;
        }}
        
        .info-value {{
            color: #333;
        }}
        
        .score-section {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            margin-bottom: 25px;
        }}
        
        .score-circle {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: white;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 8px solid {severity_color};
        }}
        
        .score-number {{
            font-size: 48px;
            font-weight: bold;
            color: {severity_color};
        }}
        
        .score-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 10px 25px;
            background: {severity_color};
            color: white;
            border-radius: 25px;
            font-weight: bold;
            font-size: 18px;
            margin-top: 10px;
        }}
        
        .report-text {{
            background: #ffffff;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            margin-bottom: 20px;
            text-align: justify;
        }}
        
        .report-text p {{
            margin-bottom: 15px;
            color: #333;
            font-size: 16px;
        }}
        
        .measurements {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .measurements h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        
        .measurement-item {{
            padding: 8px 0;
            border-bottom: 1px dashed #ddd;
        }}
        
        .measurement-item:last-child {{
            border-bottom: none;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        
        .disclaimer {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            color: #856404;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🫀 گزارش اکوکاردیوگرافی</h1>
            <div class="subtitle">گزارش هوشمند تحلیل تصاویر قلب</div>
        </div>
        
        <div class="content">
            <div class="info-card">
                <div class="info-row">
                    <span class="info-label">شناسه بیمار:</span>
                    <span class="info-value">{patient_info.get('id', 'نامشخص')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">سن:</span>
                    <span class="info-value">{patient_info.get('age', 'نامشخص')} سال</span>
                </div>
                <div class="info-row">
                    <span class="info-label">جنسیت:</span>
                    <span class="info-value">{patient_info.get('gender', 'نامشخص')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">تاریخ بررسی:</span>
                    <span class="info-value">{final_report_data.get('meta', {}).get('visit_date', 'نامشخص')}</span>
                </div>
            </div>
            
            <div class="score-section">
                <div class="score-circle">
                    <div class="score-number">{assessment.get('risk_score', 0):.1f}</div>
                    <div class="score-label">از ۱۰۰</div>
                </div>
                <div class="status-badge">{severity_emoji} {assessment.get('severity_fa', 'نرمال')}</div>
            </div>
            
            <div class="disclaimer">
                ⚠️ <strong>توجه:</strong> این گزارش توسط سیستم هوش مصنوعی تولید شده و جایگزین مشاوره پزشکی نمی‌شود. حتماً با پزشک معالج خود مشورت کنید.
            </div>
            
            <div class="report-text">
                {''.join([f'<p>{para.strip()}</p>' for para in llm_report.split('\\n\\n') if para.strip()])}
            </div>
"""
        
        # اضافه کردن اندازه‌گیری‌ها
        if echo_analysis.get("available") and echo_analysis.get("echo_measurements"):
            html += """
            <div class="measurements">
                <h3>📊 اندازه‌گیری‌های انجام شده:</h3>
"""
            for measurement in echo_analysis.get("echo_measurements", []):
                label = measurement.get("label_fa", measurement.get("parameter", ""))
                value = measurement.get("value_cm", 0)
                view = measurement.get("view", "")
                html += f"""
                <div class="measurement-item">
                    <strong>{label}:</strong> {value:.2f} سانتی‌متر <small style="color: #999;">({view})</small>
                </div>
"""
            html += """
            </div>
"""
        
        html += """
        </div>
        
        <div class="footer">
            <p>این گزارش توسط سیستم تحلیل هوشمند اکوکاردیوگرافی تولید شده است</p>
            <p>تاریخ تولید: """ + datetime.now().strftime("%Y/%m/%d - %H:%M") + """</p>
        </div>
    </div>
</body>
</html>"""
        
        return html


# تست
if __name__ == "__main__":
    # نمونه داده برای تست
    test_data = {
        "meta": {
            "visit_date": "2026-06-02"
        },
        "patient": {
            "id": "2",
            "age": 24,
            "gender": "مرد"
        },
        "overall_assessment": {
            "risk_score": 2.9,
            "severity": "MODERATE",
            "severity_fa": "متوسط"
        },
        "echo_analysis": {
            "available": True,
            "fuzzy_category_fa": "نرمال",
            "reasons": [],
            "echo_measurements": [
                {"parameter": "ivs", "label_fa": "ضخامت سپتوم", "value_cm": 0.84, "view": "plax"}
            ]
        }
    }
    
    generator = LLMReportGenerator()
    report = generator.generate_patient_report(test_data)
    print(report)

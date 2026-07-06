from __future__ import annotations

import os
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# ==============================================================================
# دیکشنری‌های ترجمه/رنگ — برای تبدیل خروجی فنی فازی به متن/ظاهر قابل‌فهم برای بیمار
# ==============================================================================

# ترجمه‌ی نام پارامترهای فازی (لاتین) و سطح شدت به فارسی، برای جایگزینی داخل reasons
_TERM_FA: dict[str, str] = {
    "la_volume":     "حجم دهلیز چپ",
    "ra_volume":     "حجم دهلیز راست",
    "lv_edv":        "حجم بطن چپ در انتهای دیاستول",
    "lv_esv":        "حجم بطن چپ در انتهای سیستول",
    "ivs_thickness": "ضخامت دیواره بین بطنی",
    "pw_thickness":  "ضخامت دیواره خلفی",
    "lv_diameter":   "قطر بطن چپ",
    "aortic_root":   "ریشه آئورت",
    "aortic_asc":    "آئورت صعودی",
    "rv_diameter":   "قطر بطن راست",
    "rv_wall":       "دیواره بطن راست",
    "pa_diameter":   "قطر شریان ریوی",
    "SEVERE":        "به طور قابل توجهی بزرگتر از حد طبیعی",
    "MILD":          "کمی بزرگتر از حد طبیعی",
    "NORMAL":        "در محدوده طبیعی",
}

_SEVERITY_COLOR: dict[str, str] = {
    "NORMAL":   "#27ae60",
    "LOW":      "#27ae60",
    "MODERATE": "#f39c12",
    "MILD":     "#f39c12",
    "HIGH":     "#e74c3c",
    "SEVERE":   "#e74c3c",
}


# ==============================================================================
# توابع کمکی HTML
# ==============================================================================

def _render_measurements_html(measurements: list[dict[str, Any]]) -> str:
    """
    ورودی:  لیست دیکشنری‌های echo_measurements
    خروجی:  "" اگه لیست خالی بود، وگرنه یک <div class="measurements">...</div> کامل
    """
    if not measurements:
        return ""
    items = "\n".join(
        f'<div class="measurement-item"><strong>{m.get("label_fa", m.get("parameter", ""))}:</strong> '
        f'{m.get("value_cm", 0):.2f} سانتی‌متر <small style="color:#999">({m.get("view", "")})</small></div>'
        for m in measurements
    )
    return f'<div class="measurements"><h3>اندازه‌گیری‌های انجام شده:</h3>{items}</div>'


def _report_css(color: str) -> str:
    """
    ورودی:  رنگ اصلی متناسب با شدت ریسک (severity accent color)
    خروجی:  استایل کامل CSS برای بلوک <style> در generate_html_report
    """
    return f"""
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               padding: 20px; line-height: 1.8; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white;
                     border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .content {{ padding: 30px; }}
        .info-card {{ background: #f8f9fa; border-radius: 10px; padding: 20px;
                     margin-bottom: 20px; border-right: 4px solid {color}; }}
        .info-row {{ display: flex; justify-content: space-between;
                    padding: 10px 0; border-bottom: 1px solid #e0e0e0; }}
        .info-row:last-child {{ border-bottom: none; }}
        .info-label {{ font-weight: bold; color: #555; }}
        .score-section {{ text-align: center; padding: 30px;
                         background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                         border-radius: 15px; margin-bottom: 25px; }}
        .score-circle {{ width: 150px; height: 150px; border-radius: 50%;
                        background: white; margin: 0 auto 20px;
                        display: flex; align-items: center; justify-content: center;
                        flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        border: 8px solid {color}; }}
        .score-number {{ font-size: 48px; font-weight: bold; color: {color}; }}
        .score-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .status-badge {{ display: inline-block; padding: 10px 25px; background: {color};
                        color: white; border-radius: 25px; font-weight: bold;
                        font-size: 18px; margin-top: 10px; }}
        .report-text {{ background: #fff; padding: 25px; border-radius: 10px;
                       border: 1px solid #e0e0e0; margin-bottom: 20px; text-align: justify; }}
        .report-text p {{ margin-bottom: 15px; color: #333; font-size: 16px; }}
        .measurements {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .measurements h3 {{ color: #333; margin-bottom: 15px; font-size: 18px; }}
        .measurement-item {{ padding: 8px 0; border-bottom: 1px dashed #ddd; }}
        .measurement-item:last-child {{ border-bottom: none; }}
        .disclaimer {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px;
                      padding: 15px; margin-bottom: 20px; color: #856404; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
        @media print {{ body {{ background: white; padding: 0; }} .container {{ box-shadow: none; }} }}
    """


# ==============================================================================
# LLMReportGenerator — pipeline.results.generate_final_patient_report ازش استفاده می‌کنه
# ==============================================================================

class LLMReportGenerator:
    """تولید گزارش نهایی با استفاده از LLM (سرویس ابری آروان)"""

    def __init__(self) -> None:
        # کلید/مدل از .env خونده می‌شه؛ بدون کلید، ساخت این کلاس همینجا fail می‌کنه
        self.api_key  = os.getenv("ARVAN_AI_API_KEY", "")
        self.api_base = os.getenv("ARVAN_AI_BASE_URL", "https://api.arvancloud.ir/llm/v1/chat/completions")
        self.model    = os.getenv("ARVAN_AI_MODEL",    "gpt-4o-mini")
        if not self.api_key:
            raise ValueError("ARVAN_AI_API_KEY not found in .env")

    def _call_llm(self, prompt: str, max_tokens: int = 800) -> str:
        """
        ورودی:  prompt نهایی، سقف توکن پاسخ
        خروجی:  متن پاسخ LLM، یا "" در صورت هر نوع خطا (تایم‌اوت، status غیر ۲۰۰، exception)
        تریس:   ۱) درخواست POST به ARVAN_AI_BASE_URL می‌فرسته (system prompt فارسی‌گو + user prompt)
                ۲) اگه ۲۰۰ برگشت، تگ‌های <think>...</think> رو حذف می‌کنه (بعضی مدل‌ها reasoning برمی‌گردونن) و trim می‌کنه
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": (
                    "تو یک دستیار پزشکی متخصص در قلب و عروق هستی که گزارش‌های اکوکاردیوگرافی را "
                    "به زبان ساده و قابل فهم برای بیماران توضیح می‌دهی.\n"
                    "قوانین: فقط فارسی بنویس، لحن محترمانه و صمیمی باشد، "
                    "از اصطلاح پزشکی پیچیده استفاده نکن، "
                    "فقط متن گزارش را بنویس بدون عنوان یا توضیحات اضافی."
                )},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens":  max_tokens,
        }
        try:
            response = requests.post(self.api_base, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                content = re.sub(r"<think>[\s\S]*?(</think>|\Z)", "", content)
                return content.strip()
            print(f"LLM API Error: {response.status_code} - {response.text}")
        except Exception as exc:
            print(f"Error calling LLM: {exc}")
        return ""

    def _build_prompt(self, data: dict[str, Any]) -> str:
        """
        ورودی:  final_report_data (خروجی ai_service.report_generator.build_final_report)
        خروجی:  پرامپت فارسی آماده برای ارسال به LLM، شامل امتیاز ریسک + دلایل ترجمه‌شده به فارسی
        """
        patient    = data.get("patient", {})
        assessment = data.get("overall_assessment", {})
        echo       = data.get("echo_analysis", {})

        age        = patient.get("age", "نامشخص")
        gender_raw = patient.get("gender", "male")
        gender     = "مرد" if gender_raw in ("male", "مرد", "m", 1, 2) else "زن"
        severity   = assessment.get("severity_fa", "نرمال")
        risk_score = assessment.get("risk_score", 0)
        reasons    = echo.get("reasons", [])
        risk_factors = data.get("risk_factors", [])

        lines = [
            f"به یک بیمار {age} ساله {gender} که اکوکاردیوگرافی انجام داده، گزارش نتیجه را توضیح بده.",
            "",
            "اطلاعات کلی:",
            f"- امتیاز ریسک کلی: {risk_score:.1f} از ۱۰۰",
            f"- وضعیت: {severity}",
            f"- نتیجه تحلیل اکو: {echo.get('fuzzy_category_fa', 'نرمال')}",
            "",
        ]

        if reasons:
            lines.append("نکات قابل توجه در بررسی:")
            for r in reasons:
                fa = r
                for eng, persian in _TERM_FA.items():
                    fa = fa.replace(eng, persian)
                lines.append(f"- {fa}")
        else:
            lines.append("- تمام پارامترهای بررسی‌شده در محدوده طبیعی هستند")

        if risk_factors:
            lines.append("")
            lines.append("عوامل خطر بالینی شناسایی‌شده:")
            for rf in risk_factors:
                label = rf.get("label_fa") if isinstance(rf, dict) else rf
                if label:
                    lines.append(f"- {label}")

        lines += [
            "",
            "لطفاً یک گزارش ۳ تا ۴ پاراگرافی بنویس که شامل این موارد باشد:",
            "۱. توضیح کلی وضعیت قلب بیمار (به زبان ساده)",
            "۲. معنی نتایج برای سلامت بیمار",
            "۳. توصیه‌های عملی برای نگهداری سلامت قلب",
            "۴. آیا نیاز به پیگیری بیشتر هست یا خیر",
            "",
            "مهم: فقط متن گزارش را بنویس، بدون عنوان یا header.",
        ]
        return "\n".join(lines)

    def generate_patient_report(self, final_report_data: dict[str, Any]) -> str:
        """
        ورودی:  final_report_data
        خروجی:  متن گزارش فارسی برای بیمار
        تریس:   می‌ره داخل _build_prompt → _call_llm؛ اگه LLM جواب نداد (متن خالی)، یک متن fallback ثابت جایگزین می‌شه
        """
        text = self._call_llm(self._build_prompt(final_report_data))
        if not text:
            severity = final_report_data.get("overall_assessment", {}).get("severity_fa", "نرمال")
            text = (
                f"با سلام و احترام،\n\n"
                f"نتایج بررسی اکوکاردیوگرافی شما نشان می‌دهد که وضعیت قلب شما در وضعیت {severity} قرار دارد.\n\n"
                "لطفاً برای دریافت توضیحات کامل با پزشک معالج خود مشورت کنید.\n\nبا آرزوی سلامتی"
            )
        return text

    def generate_html_report(self, llm_report: str, final_report_data: dict[str, Any]) -> str:
        """
        ورودی:  llm_report (متن خروجی generate_patient_report)، final_report_data
        خروجی:  رشته‌ی کامل HTML قابل ذخیره/نمایش (شامل CSS و اطلاعات بیمار)
        """
        patient    = final_report_data.get("patient", {})
        assessment = final_report_data.get("overall_assessment", {})
        echo       = final_report_data.get("echo_analysis", {})
        color      = _SEVERITY_COLOR.get(assessment.get("severity", "NORMAL"), "#95a5a6")

        paragraphs_html   = "".join(f"<p>{p.strip()}</p>" for p in llm_report.split("\n\n") if p.strip())
        measurements_html = (
            _render_measurements_html(echo.get("echo_measurements", []))
            if echo.get("available") and echo.get("echo_measurements") else ""
        )

        return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>گزارش اکوکاردیوگرافی</title>
    <style>{_report_css(color)}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>گزارش اکوکاردیوگرافی</h1>
            <div>گزارش هوشمند تحلیل تصاویر قلب</div>
        </div>
        <div class="content">
            <div class="info-card">
                <div class="info-row">
                    <span class="info-label">شناسه بیمار:</span>
                    <span>{patient.get('id', 'نامشخص')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">سن:</span>
                    <span>{patient.get('age', 'نامشخص')} سال</span>
                </div>
                <div class="info-row">
                    <span class="info-label">جنسیت:</span>
                    <span>{patient.get('gender', 'نامشخص')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">تاریخ بررسی:</span>
                    <span>{final_report_data.get('meta', {}).get('visit_date', 'نامشخص')}</span>
                </div>
            </div>
            <div class="score-section">
                <div class="score-circle">
                    <div class="score-number">{assessment.get('risk_score', 0):.1f}</div>
                    <div class="score-label">از ۱۰۰</div>
                </div>
                <div class="status-badge">{assessment.get('severity_fa', 'نرمال')}</div>
            </div>
            <div class="disclaimer">
                <strong>توجه:</strong> این گزارش توسط سیستم هوش مصنوعی تولید شده و جایگزین مشاوره پزشکی نمی‌شود.
            </div>
            <div class="report-text">{paragraphs_html}</div>
            {measurements_html}
        </div>
        <div class="footer">
            <p>این گزارش توسط سیستم تحلیل هوشمند اکوکاردیوگرافی تولید شده است</p>
            <p>تاریخ تولید: {datetime.now().strftime("%Y/%m/%d - %H:%M")}</p>
        </div>
    </div>
</body>
</html>"""

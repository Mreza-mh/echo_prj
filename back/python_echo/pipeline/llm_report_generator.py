from __future__ import annotations

import os
import re
import requests
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# ==============================================================================
# ترجمه‌ی نام پارامترهای فازی (لاتین) و سطح شدت به فارسی، برای جایگزینی داخل reasons
# ==============================================================================
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


# ==============================================================================
# LLMReportGenerator — pipeline.results.generate_and_save_final_report ازش استفاده می‌کنه
# ==============================================================================

class LLMReportGenerator:

    def __init__(self) -> None:
        # کلید/مدل از .env خونده می‌شه؛ بدون کلید، ساخت این کلاس همینجا fail می‌کنه
        self.api_key  = os.getenv("ARVAN_AI_API_KEY", "")
        self.api_base = os.getenv("ARVAN_AI_BASE_URL", "https://api.arvancloud.ir/llm/v1/chat/completions")
        self.model    = os.getenv("ARVAN_AI_MODEL",    "gpt-4o-mini")
        if not self.api_key:
            raise ValueError("ARVAN_AI_API_KEY not found in .env")

    # قوانین لحن/فرمت فقط همین‌جا (system) تعریف می‌شوند تا در user prompt تکرار نشوند
    _SYSTEM_PROMPT = (
        "تو متخصص قلب هستی و نتیجه‌ی اکوکاردیوگرافی را برای بیمار توضیح می‌دهی.\n"
        "به فارسی، محترمانه و ساده (بدون اصطلاح پیچیده) بنویس.\n"
        "۳ تا ۴ پاراگراف کوتاه: وضعیت کلی قلب، معنی نتایج، توصیه‌های عملی و لزوم پیگیری.\n"
        "فقط متن گزارش را بنویس، بدون عنوان یا header."
    )

    def _call_llm(self, prompt: str, max_tokens: int = 600) -> str:
        # """
        # ورودی:  prompt نهایی، سقف توکن پاسخ
        # خروجی:  متن پاسخ LLM، یا "" در صورت هر نوع خطا (تایم‌اوت، status غیر ۲۰۰، exception)
        # تریس:   ۱) درخواست POST به ARVAN_AI_BASE_URL می‌فرسته (system prompt + user prompt)
        #         ۲) اگه ۲۰۰ برگشت، تگ‌های <think>...</think> رو حذف می‌کنه (بعضی مدل‌ها reasoning برمی‌گردونن) و trim می‌کنه
        # """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens":  max_tokens,
        }
        try:
            response = requests.post(self.api_base, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                content = re.sub(r"<think>[\s\S]*?(</think>|\Z)", "", content)
                return content.strip()
            print(f"LLM API Error: {response.status_code} - {response.text}")
        except Exception as exc:
            print(f"Error calling LLM: {exc}")
        return ""

    def _build_prompt(self, data: dict[str, Any]) -> str:
        # """
        # ورودی:  final_report_data (خروجی pipeline.results._build_final_report_data)
        # خروجی:  user prompt — فقط داده‌ی بیمار؛ دستورالعمل لحن/فرمت در _SYSTEM_PROMPT است
        # """
        patient    = data.get("patient", {})
        assessment = data.get("overall_assessment", {})
        echo       = data.get("echo_analysis", {})

        gender_raw = patient.get("gender", "male")
        gender     = "مرد" if gender_raw in ("male", "مرد", "m", 1, 2) else "زن"

        lines = [
            f"بیمار: {patient.get('age', 'نامشخص')} ساله، {gender}",
            f"امتیاز ریسک: {assessment.get('risk_score', 0):.1f} از ۱۰۰ ({assessment.get('severity_fa', 'نرمال')})",
            f"نتیجه اکو: {echo.get('fuzzy_category_fa', 'نرمال')}",
        ]

        reasons = echo.get("reasons", [])
        if reasons:
            lines.append("یافته‌های اکو:")
            for r in reasons:
                r = r.replace(" is ", " ")  # reasons به شکل "la_volume is MILD" می‌آیند
                for eng, persian in _TERM_FA.items():
                    r = r.replace(eng, persian)
                lines.append(f"- {r}")

        risk_factors = data.get("risk_factors", [])
        if risk_factors:
            lines.append("عوامل خطر بالینی:")
            for rf in risk_factors:
                label = rf.get("label_fa") if isinstance(rf, dict) else rf
                if label:
                    lines.append(f"- {label}")

        return "\n".join(lines)

    def generate_patient_report(self, final_report_data: dict[str, Any]) -> str:
        # """
        # ورودی:  final_report_data
        # خروجی:  متن گزارش فارسی برای بیمار
        # تریس:   می‌ره داخل _build_prompt → _call_llm؛ اگه LLM جواب نداد (متن خالی)، یک متن fallback ثابت جایگزین می‌شه
        # """
        text = self._call_llm(self._build_prompt(final_report_data))
        if not text:
            severity = final_report_data.get("overall_assessment", {}).get("severity_fa", "نرمال")
            text = (
                f"با سلام و احترام،\n\n"
                f"نتایج بررسی اکوکاردیوگرافی شما نشان می‌دهد که وضعیت قلب شما در وضعیت {severity} قرار دارد.\n\n"
                "لطفاً برای دریافت توضیحات کامل با پزشک معالج خود مشورت کنید.\n\nبا آرزوی سلامتی"
            )
        return text

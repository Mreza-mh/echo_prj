"""
CardioAI — Final Report Generator
==================================
ترکیب خروجی‌های سه لایه تحلیلی برای تولید گزارش نهایی:

  1. ML Analysis  : نتایج HD_LogisticRegression + CV_CatBoost
  2. Echo/Fuzzy   : نتایج منطق فازی از ویدیوهای اکوکاردیوگرافی
  3. Patient Info : اطلاعات دموگرافیک از MongoDB

گزارش در دو نسخه تولید می‌شود:
  • doctor_report  : فنی / بالینی با تمام اعداد و شاخص‌ها
  • patient_report : ساده / قابل فهم برای بیمار
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── Severity / Category mappings ────────────────────────────────────────────
_SEVERITY_META: Dict[str, Dict[str, str]] = {
    "LOW":      {"emoji": "🟢", "fa": "پایین",  "en": "Low",      "color": "#27ae60"},
    "MODERATE": {"emoji": "🟡", "fa": "متوسط", "en": "Moderate", "color": "#f39c12"},
    "HIGH":     {"emoji": "🔴", "fa": "بالا",   "en": "High",     "color": "#e74c3c"},
}
_FUZZY_TO_SEVERITY = {"normal": "LOW", "mild": "MODERATE", "severe": "HIGH"}

_PARAM_LABELS_FA: Dict[str, str] = {
    "aortic_root":   "ریشه آئورت",
    "aortic_asc":    "آئورت صعودی",
    "la_volume":     "حجم دهلیز چپ",
    "ra_volume":     "حجم دهلیز راست",
    "lv_edv":        "حجم پایان دیاستولی بطن چپ",
    "lv_esv":        "حجم پایان سیستولی بطن چپ",
    "ivs_thickness": "ضخامت سپتوم بین‌بطنی",
    "pw_thickness":  "ضخامت دیواره خلفی",
    "lv_diameter":   "قطر بطن چپ",
    "rv_diameter":   "قطر بطن راست",
    "rv_wall":       "ضخامت دیواره بطن راست",
    "pa_diameter":   "قطر شریان ریوی",
}


# ─── Utility helpers ─────────────────────────────────────────────────────────

def _sev(label: str) -> Dict[str, str]:
    return _SEVERITY_META.get(label.upper(), _SEVERITY_META["MODERATE"])


def _bar(prob: float, width: int = 20) -> str:
    """نوار پیشرفت ASCII"""
    filled = round(max(0.0, min(1.0, prob)) * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {prob * 100:.1f}%"


def _quality(conf: float) -> str:
    if conf >= 0.80: return "خوب ✅"
    if conf >= 0.50: return "متوسط ⚠️"
    return "ناکافی ❌ (داده‌های تکمیلی نیاز است)"


def _gender_fa(raw: Any) -> str:
    g = str(raw).lower()
    return "مرد" if g in ("male", "مرد", "m", "2") else "زن"


def _overall_severity(
    ml:    Optional[Dict[str, Any]],
    fuzzy: Optional[Dict[str, Any]],
) -> str:
    """بدترین (بالاترین) ریسک بین ML و Fuzzy را برمی‌گرداند"""
    order = {"LOW": 0, "MODERATE": 1, "HIGH": 2}

    ml_sev  = (ml or {}).get("severity", "MODERATE")
    fuzz_cat = (fuzzy or {}).get("category", "Normal")
    fuzz_sev = _FUZZY_TO_SEVERITY.get(fuzz_cat.lower(), "MODERATE")

    return ml_sev if order.get(ml_sev, 1) >= order.get(fuzz_sev, 1) else fuzz_sev


def _overall_score(
    ml:    Optional[Dict[str, Any]],
    fuzzy: Optional[Dict[str, Any]],
) -> float:
    """میانگین امتیاز ML و Fuzzy"""
    scores: List[float] = []
    if ml:
        scores.append(float(ml.get("combined_score", 50.0)))
    if fuzzy and "score" in fuzzy:
        scores.append(float(fuzzy["score"]))
    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _clinical_recommendation(
    severity: str,
    ml:       Optional[Dict[str, Any]],
    fuzzy:    Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """تولید توصیه بالینی بر اساس سطح ریسک"""
    risk_factors = (ml or {}).get("risk_factors", [])
    rf_labels = [rf["label_fa"] for rf in risk_factors]

    if severity == "HIGH":
        return {
            "urgency":   "فوری",
            "doctor":    (
                "ارجاع فوری به متخصص قلب توصیه می‌شود. "
                "انجام ECG، اکوکاردیوگرافی کامل، تست ورزش و پنل لیپیدی ضروری است. "
                "بررسی درمان دارویی (آنتی‌هیپرتانسیو، استاتین، آنتی‌پلاکت) در دستور کار باشد."
            ),
            "patient":   (
                "لطفاً هر چه زودتر به متخصص قلب مراجعه کنید. "
                "برخی شاخص‌های سلامت قلب شما نیاز به بررسی تخصصی فوری دارند."
            ),
            "lifestyle": (
                "ترک فوری سیگار، کاهش مصرف نمک و چربی اشباع، "
                "ورزش سبک با نظر پزشک، کنترل روزانه فشار خون."
            ),
        }
    elif severity == "MODERATE":
        return {
            "urgency":   "زودهنگام",
            "doctor":    (
                "پیگیری دوره‌ای هر ۳–۶ ماه توصیه می‌شود. "
                "بررسی و اصلاح عوامل خطر قابل تغییر (فشار خون، کلسترول، وزن). "
                "آموزش تغییر سبک زندگی."
            ),
            "patient":   (
                "شاخص‌های قلبی شما در محدوده ریسک متوسط است. "
                "با تغییرات سبک زندگی و پیگیری منظم می‌توانید این ریسک را کاهش دهید."
            ),
            "lifestyle": (
                "ورزش منظم هوازی (حداقل ۱۵۰ دقیقه در هفته)، "
                "رژیم مدیترانه‌ای، کاهش استرس، کنترل وزن."
            ),
        }
    else:
        return {
            "urgency":   "روتین",
            "doctor":    "یافته‌ها در محدوده طبیعی. ارزیابی سالانه پیشنهاد می‌شود.",
            "patient":   (
                "خبر خوب: شاخص‌های قلبی شما وضعیت مطلوبی دارند. "
                "ادامه سبک زندگی سالم را فراموش نکنید."
            ),
            "lifestyle": "ورزش منظم، رژیم متعادل، عدم مصرف دخانیات، کنترل سالانه.",
        }


def _extract_echo_measurements(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """استخراج اندازه‌گیری‌های اکو از ردیف‌های pipeline"""
    seen  = set()
    out: List[Dict[str, Any]] = []

    for row in rows:
        mname = row.get("measurement_name", "")
        val   = row.get("length_cm")
        if not mname or val is None or mname in seen:
            continue
        seen.add(mname)
        out.append({
            "parameter": mname,
            "label_fa":  _PARAM_LABELS_FA.get(mname, mname),
            "value_cm":  round(float(val), 3),
            "view":      row.get("detected_view", ""),
        })
    return out


# ─── Main builder ─────────────────────────────────────────────────────────────

def build_final_report(
    patient_config: Dict[str, Any],
    ml_result:      Optional[Dict[str, Any]],
    fuzzy_result:   Optional[Dict[str, Any]],
    echo_rows:      Optional[List[Dict[str, Any]]] = None,
    visit_date:     Optional[str] = None,
) -> Dict[str, Any]:
    """
    ساخت گزارش جامع نهایی از همه منابع تحلیلی.

    Args:
        patient_config : اطلاعات بیمار از MongoDB
        ml_result      : خروجی MLRiskPredictor.predict()
        fuzzy_result   : خروجی aggregate_and_evaluate_fuzzy()
        echo_rows      : لیست ردیف‌های اندازه‌گیری از process_video()
        visit_date     : تاریخ ویزیت (YYYY-MM-DD)، پیش‌فرض: امروز

    Returns:
        dict کامل با کلیدهای:
          patient, overall_assessment, ml_analysis, echo_analysis,
          risk_factors, recommendation, doctor_report, patient_report
    """
    now        = datetime.now()
    visit_date = visit_date or now.strftime("%Y-%m-%d")
    echo_rows  = echo_rows or []

    # ── Patient info ──────────────────────────────────────────────────────
    pid        = str(patient_config.get("user_id", patient_config.get("id", "N/A")))
    age        = patient_config.get("age", "N/A")
    gender_raw = patient_config.get("gender", patient_config.get("sex", ""))
    weight     = patient_config.get("weight")
    height     = patient_config.get("height")
    bmi        = (ml_result or {}).get("bmi")

    # ── Risk assessment ───────────────────────────────────────────────────
    sev        = _overall_severity(ml_result, fuzzy_result)
    score      = _overall_score(ml_result, fuzzy_result)
    sev_meta   = _sev(sev)
    rec        = _clinical_recommendation(sev, ml_result, fuzzy_result)
    echo_meas  = _extract_echo_measurements(echo_rows)
    risk_factors = (ml_result or {}).get("risk_factors", [])

    # ── ML section ────────────────────────────────────────────────────────
    ml_section: Dict[str, Any] = {"available": False}
    if ml_result:
        hd = ml_result.get("hd_result", {})
        cv = ml_result.get("cv_result", {})
        ml_section = {
            "available": True,
            "hd_model": {
                "name":              hd.get("model", "HD_LogisticRegression"),
                "probability":       hd.get("probability", 0.5),
                "probability_pct":   hd.get("probability_pct", 50.0),
                "confidence":        hd.get("confidence", 0.0),
                "data_quality":      _quality(hd.get("confidence", 0.0)),
                "missing_features":  hd.get("missing_features", []),
            },
            "cv_model": {
                "name":              cv.get("model", "CV_CatBoost"),
                "probability":       cv.get("probability", 0.5),
                "probability_pct":   cv.get("probability_pct", 50.0),
                "confidence":        cv.get("confidence", 0.0),
                "data_quality":      _quality(cv.get("confidence", 0.0)),
                "missing_features":  cv.get("missing_features", []),
            },
            "combined_score":    ml_result.get("combined_score", 50.0),
            "combined_prob":     ml_result.get("combined_prob", 0.5),
            "overall_severity":  ml_result.get("severity", "MODERATE"),
            "overall_confidence": ml_result.get("confidence", 0.0),
        }

    # ── Echo/Fuzzy section ────────────────────────────────────────────────
    echo_section: Dict[str, Any] = {"available": False}
    if fuzzy_result:
        fuzz_cat = fuzzy_result.get("category", "Unknown")
        fuzz_cat_fa = {"Normal": "نرمال", "Mild": "خفیف", "Severe": "شدید"}.get(fuzz_cat, fuzz_cat)
        echo_section = {
            "available":      True,
            "fuzzy_score":    float(fuzzy_result.get("score", 0)),
            "fuzzy_category": fuzz_cat,
            "fuzzy_category_fa": fuzz_cat_fa,
            "reasons":        fuzzy_result.get("reasons", []),
            "echo_measurements": echo_meas,
        }

    report = {
        "meta": {
            "generated_at":   now.isoformat(),
            "visit_date":     visit_date,
            "report_version": "2.0",
            "pipeline":       "CardioAI (ML + Fuzzy + Echo)",
        },
        "patient": {
            "id":        pid,
            "age":       age,
            "gender":    _gender_fa(gender_raw),
            "weight_kg": weight,
            "height_cm": height,
            "bmi":       bmi,
        },
        "overall_assessment": {
            "risk_score":       score,
            "severity":         sev,
            "severity_fa":      sev_meta["fa"],
            "severity_emoji":   sev_meta["emoji"],
            "severity_color":   sev_meta["color"],
        },
        "ml_analysis":    ml_section,
        "echo_analysis":  echo_section,
        "risk_factors":   risk_factors,
        "recommendation": rec,
        "doctor_report":  _build_doctor_report(
            patient_config, ml_result, fuzzy_result,
            echo_meas, risk_factors, sev, score, rec, visit_date, bmi
        ),
        "patient_report": _build_patient_report(
            patient_config, ml_result, fuzzy_result,
            echo_meas, risk_factors, sev, score, rec, visit_date
        ),
    }
    return report


# ─── Doctor Report ────────────────────────────────────────────────────────────

def _build_doctor_report(
    patient_config: Dict,
    ml:             Optional[Dict],
    fuzzy:          Optional[Dict],
    echo_meas:      List[Dict],
    risk_factors:   List[Dict],
    severity:       str,
    score:          float,
    rec:            Dict[str, str],
    visit_date:     str,
    bmi:            Optional[float],
) -> str:
    sev_info   = _sev(severity)
    pid        = patient_config.get("user_id", patient_config.get("id", "N/A"))
    age        = patient_config.get("age", "N/A")
    gender_raw = patient_config.get("gender", patient_config.get("sex", ""))
    weight     = patient_config.get("weight", "N/A")
    height     = patient_config.get("height", "N/A")

    sep = "─" * 65

    lines = [
        "═" * 65,
        "  CARDIOVASCULAR AI ANALYSIS — گزارش پزشک",
        "  Powered by: ML Ensemble + Fuzzy Echo Analysis",
        "═" * 65,
        f"  شناسه بیمار  : {pid}",
        f"  تاریخ        : {visit_date}",
        f"  سن / جنسیت  : {age} سال / {_gender_fa(gender_raw)}",
        f"  وزن / قد    : {weight} kg / {height} cm",
    ]
    if bmi:
        lines.append(f"  BMI           : {bmi:.1f} kg/m²")
    lines += [sep, ""]

    # ── Overall ──────────────────────────────────────────────────────────
    lines += [
        "  ── ارزیابی کلی ──────────────────────────────────────────────",
        f"  امتیاز ریسک ترکیبی  : {score:.1f} / 100",
        f"  طبقه‌بندی شدت       : {sev_info['emoji']}  {sev_info['fa'].upper()}  ({severity})",
        "",
    ]

    # ── ML Models ────────────────────────────────────────────────────────
    if ml:
        hd = ml.get("hd_result", {})
        cv = ml.get("cv_result", {})
        lines += [
            "  ── مدل‌های یادگیری ماشین ────────────────────────────────────",
            f"  {hd.get('model', 'HD_LR'):<35} {_bar(hd.get('probability', 0.5))}",
            f"     کیفیت داده  : {_quality(hd.get('confidence', 0))}",
            f"     داده‌های جایگزین: {', '.join(hd.get('missing_features', [])[:4]) or 'ندارد'}",
            "",
            f"  {cv.get('model', 'CV_CatBoost'):<35} {_bar(cv.get('probability', 0.5))}",
            f"     کیفیت داده  : {_quality(cv.get('confidence', 0))}",
            f"     داده‌های جایگزین: {', '.join(cv.get('missing_features', [])[:4]) or 'ندارد'}",
            "",
            f"  امتیاز ترکیبی ML  : {ml.get('combined_score', 50):.1f} / 100",
            f"  اطمینان کلی       : {ml.get('confidence', 0)*100:.0f}%",
            "",
        ]

    # ── Fuzzy Echo ────────────────────────────────────────────────────────
    if fuzzy:
        cat = fuzzy.get("category", "Unknown")
        cat_fa = {"Normal": "نرمال", "Mild": "خفیف", "Severe": "شدید"}.get(cat, cat)
        lines += [
            "  ── تحلیل اکوکاردیوگرافی (منطق فازی) ─────────────────────",
            f"  امتیاز فازی  : {float(fuzzy.get('score', 0)):.1f} / 100",
            f"  دسته‌بندی    : {_sev(_FUZZY_TO_SEVERITY.get(cat.lower(), 'MODERATE'))['emoji']} {cat} ({cat_fa})",
        ]
        reasons = fuzzy.get("reasons", [])
        if reasons:
            lines.append("  یافته‌های غیرنرمال اکو:")
            for r in reasons:
                lines.append(f"    ⚠️  {r}")
        else:
            lines.append("  ✅ تمام پارامترهای اکو در محدوده نرمال")
        lines.append("")

    # ── Echo Measurements ─────────────────────────────────────────────────
    if echo_meas:
        lines += ["  ── اندازه‌گیری‌های اکو از ویدیو ──────────────────────────"]
        for m in echo_meas:
            lines.append(
                f"  {m['label_fa']:<32}: {m['value_cm']:.2f} cm  "
                f"[نما: {m.get('view', '?')}]"
            )
        lines.append("")

    # ── Risk Factors ──────────────────────────────────────────────────────
    if risk_factors:
        lines += ["  ── عوامل خطر بالینی شناسایی‌شده ─────────────────────────"]
        for rf in risk_factors:
            lines.append(
                f"  ⚠️  {rf['label_fa']:<40} "
                f"[{rf['feature']}={rf['value']}]"
            )
        lines.append("")

    # ── Recommendation ────────────────────────────────────────────────────
    lines += [
        "  ── توصیه بالینی ─────────────────────────────────────────────",
        f"  فوریت      : {rec['urgency']}",
        f"  اقدام بالینی:",
        f"    {rec['doctor']}",
        f"  سبک زندگی :",
        f"    {rec['lifestyle']}",
        "",
        "  ── سلب مسئولیت ──────────────────────────────────────────────",
        "  این گزارش توسط سیستم هوش مصنوعی تولید شده است.",
        "  جایگزین قضاوت بالینی متخصص نمی‌شود.",
        "  تمام یافته‌ها باید توسط پزشک متخصص تأیید شوند.",
        "═" * 65,
    ]

    return "\n".join(lines)


# ─── Patient Report ───────────────────────────────────────────────────────────

def _build_patient_report(
    patient_config: Dict,
    ml:             Optional[Dict],
    fuzzy:          Optional[Dict],
    echo_meas:      List[Dict],
    risk_factors:   List[Dict],
    severity:       str,
    score:          float,
    rec:            Dict[str, str],
    visit_date:     str,
) -> str:
    sev_info   = _sev(severity)
    pid        = patient_config.get("user_id", patient_config.get("id", "N/A"))
    age        = patient_config.get("age", "N/A")

    # گیج بصری از 0 تا 100
    gauge_filled = round(score / 5)
    gauge = "█" * gauge_filled + "░" * (20 - gauge_filled)

    lines = [
        "═" * 60,
        "  گزارش ارزیابی سلامت قلب شما",
        "═" * 60,
        f"  تاریخ: {visit_date}  |  سن: {age} سال",
        "─" * 60,
        "",
        "  ── وضعیت کلی قلب شما ────────────────────────────────────",
        f"  [{gauge}]",
        f"   ۰             ۵۰             ۱۰۰",
        f"   (بدون ریسک)         (ریسک بالا)",
        "",
        f"  امتیاز کلی   : {score:.0f} / ۱۰۰",
        f"  وضعیت قلب    : {sev_info['emoji']} {sev_info['fa']}",
        "",
    ]

    # ── ML results (ساده) ──────────────────────────────────────────────
    if ml:
        hd_pct = ml.get("hd_result", {}).get("probability_pct", 50)
        cv_pct = ml.get("cv_result", {}).get("probability_pct", 50)
        lines += [
            "  ── نتایج آزمون‌های هوشمند ───────────────────────────────",
            f"  📊 ریسک بیماری قلبی (بر اساس ECG/ورزش) : {hd_pct:.0f}٪",
            f"  📊 ریسک قلبی-عروقی (فشار خون/سبک زندگی): {cv_pct:.0f}٪",
            "",
        ]

    # ── Echo results (ساده) ────────────────────────────────────────────
    if fuzzy:
        cat = fuzzy.get("category", "Normal")
        cat_fa = {"Normal": "نرمال ✅", "Mild": "خفیف ⚠️", "Severe": "شدید 🔴"}.get(cat, cat)
        lines += [
            "  ── نتایج بررسی تصویری قلب (اکو) ───────────────────────",
            f"  وضعیت ساختار قلب : {cat_fa}",
        ]
        reasons = fuzzy.get("reasons", [])
        if reasons:
            lines.append("  موارد نیاز به توجه:")
            for r in reasons:
                lines.append(f"    • {r}")
        else:
            lines.append("  ✅ ساختار قلب در اندازه‌های طبیعی قرار دارد.")
        lines.append("")

    # ── Risk factors (به زبان ساده) ────────────────────────────────────
    if risk_factors:
        lines += ["  ── عواملی که می‌توانند بر ریسک تأثیر بگذارند ─────────"]
        for rf in risk_factors:
            lines.append(f"  ⚠️  {rf['label_fa']}")
        lines.append("")

    # ── Recommendation ────────────────────────────────────────────────
    lines += [
        "  ── توصیه پزشکی ─────────────────────────────────────────",
        f"  {rec['patient']}",
        "",
        "  ── تغییرات سبک زندگی پیشنهادی ─────────────────────────",
        f"  {rec['lifestyle']}",
        "",
        "─" * 60,
        "  * این گزارش اطلاعاتی است و جایگزین مشاوره پزشکی نمی‌شود.",
        "  * حتماً نتایج را با پزشک خود در میان بگذارید.",
        "═" * 60,
    ]
    return "\n".join(lines)


# ─── Save helper ──────────────────────────────────────────────────────────────

def save_report(
    report:    Dict[str, Any],
    save_dir:  Path,
    patient_id: str,
    visit_date: str,
) -> Dict[str, str]:
    """
    ذخیره گزارش نهایی در چند فرمت.

    Returns: dict مسیرهای ذخیره‌شده
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    saved: Dict[str, str] = {}

    # JSON کامل
    json_path = save_dir / "final_report.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    saved["json"] = str(json_path)

    # گزارش پزشک (txt)
    dr_path = save_dir / "doctor_report.txt"
    with dr_path.open("w", encoding="utf-8") as f:
        f.write(report.get("doctor_report", ""))
    saved["doctor_txt"] = str(dr_path)

    # گزارش بیمار (txt)
    pt_path = save_dir / "patient_report.txt"
    with pt_path.open("w", encoding="utf-8") as f:
        f.write(report.get("patient_report", ""))
    saved["patient_txt"] = str(pt_path)

    # خلاصه ML (json کوچک)
    ml_path = save_dir / "ml_result.json"
    ml_summary = {
        "visit_date":   visit_date,
        "patient_id":   patient_id,
        "overall": {
            "score":    report["overall_assessment"]["risk_score"],
            "severity": report["overall_assessment"]["severity"],
        },
        "ml_analysis":  report.get("ml_analysis", {}),
        "risk_factors": [
            {"feature": r["feature"], "label": r["label_fa"]}
            for r in report.get("risk_factors", [])
        ],
        "recommendation_urgency": report.get("recommendation", {}).get("urgency", ""),
    }
    with ml_path.open("w", encoding="utf-8") as f:
        json.dump(ml_summary, f, indent=2, ensure_ascii=False, default=str)
    saved["ml_json"] = str(ml_path)

    return saved
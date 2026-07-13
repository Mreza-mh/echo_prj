"""
pipeline.results — ذخیره‌سازی تمام خروجی‌های پایپ‌لاین (دیسک + MongoDB)

ترتیب بخش‌های این فایل همان ترتیب اجرای پایپ‌لاین است (main.py):

  ۱. ابزارهای مسیر/فایل        : هلپرهای عمومی که همه‌ی بخش‌ها استفاده می‌کنند
  ۲. لایه‌ی MongoDB             : _mongo_upsert_visit — تنها نقطه‌ی نوشتن در مونگو
  ۳. خروجی هر ویدیو (per-view) : setup_video_session → save_reports
  ۴. جمع‌بندی فازی               : aggregate_and_evaluate_fuzzy   (entry: fuzzy_summary)
  ۵. گزارش نهایی + LLM          : generate_and_save_final_report (entry: llm_final_report)

هر خروجی دو نسخه دارد: internal (کامل، برای دیباگ) و public (چیزی که فرانت نشان می‌دهد).

──────────────────────────────────────────────────────────────────────────────
فایل‌های روی دیسک (زیرِ  <output_root>/<patient_id>/<visit_date>/ ):
  <view>/                        ← هر ویدیو (بخش ۳): result.json + measurements.csv + internal/
  summary_<views>_<HH_MM>/       ← فازی (بخش ۴):   fuzzy_summary.json + نمودارها
  final_report/                  ← گزارش نهایی (بخش ۵): final_report.json + llm_patient_report.txt

سند MongoDB (collection «patients»، یکی به‌ازای هر بیمار):
  { _id, patient_info, last_updated,
    visits: { "<visit_date>": [ ...entryها... ] } }

  هر ویزیت یک آرایه از entryهاست که با فیلد type/view_instance از هم جدا می‌شوند:
    • { view_instance, measurements, a4c_volume, ... }   ← per-view (type ندارد)
    • { type: "fuzzy_summary",    result, aggregated_data, ... }
    • { type: "llm_final_report", report_text, ... }
  فرانت با همین type بین‌شان تفکیک می‌کند (visit.type در تمپلیت).
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# ریشه‌ی پروژه (echo_prj) — برای محاسبه‌ی مسیر نسبی فایل‌ها نسبت به کل پروژه
PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ==============================================================================
# ۱) ابزارهای مسیر/فایل
# ==============================================================================

def _public_root_override() -> Path | None:
    # اگر .env مسیر public لاراول را ست کرده باشد (LARAVEL_PUBLIC_RESULT_PATH) همان برمی‌گردد
    public_root = os.getenv("LARAVEL_PUBLIC_RESULT_PATH")
    return Path(public_root).expanduser().resolve() if public_root else None


def get_public_output_root(output_root: Path) -> Path:
    # مسیر ریشه‌ی خروجی‌های public؛ بدون override همان output_root است
    return _public_root_override() or output_root.expanduser().resolve()


def path_for_frontend(path_value: str | Path | None) -> str | None:
    # مسیر مطلق → مسیر نسبی قابل استفاده در فرانت/MongoDB
    # (نسبت به public root یا ریشه‌ی پروژه؛ اگر هیچ‌کدام match نشد خود مسیر مطلق برمی‌گردد)
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    for root in filter(None, [_public_root_override(), PROJECT_ROOT.resolve()]):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return str(path)


def relative_to_root(path_value: str | Path | None, output_root: Path) -> str | None:
    # مسیر نسبی به output_root؛ اگر زیرمجموعه نبود مسیر مطلق برمی‌گردد
    # (مصرف‌کننده: pipeline.processing برای مسیرهای داخل سطرهای اندازه‌گیری)
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    try:
        return str(path.relative_to(output_root.resolve()))
    except ValueError:
        return str(path)


def safe_name(value: str) -> str:
    # کاراکترهای غیر الفبایی/عددی → «_» تا اسم پوشه/فایل امن شود
    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip())
    return safe.strip("_") or "item"


def ensure_dir(path: Path) -> Path:
    # پوشه (و والدینش) را می‌سازد اگر نبود؛ خودش را برمی‌گرداند (برای chain کردن)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(data: dict[str, Any], output_path: Path) -> None:
    # ذخیره‌ی خوانا (indent=2) با پشتیبانی فارسی؛ default=str برای فیلدهای datetime
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, default=str)


def copy_public_file(source: str | Path | None, destination: Path) -> str | None:
    # کپی فیزیکی فایل از internal → public؛ خروجی: مسیر نسبی برای فرانت، یا None اگر source نبود
    if not source:
        return None
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source_path, destination)
    return path_for_frontend(destination)


# ==============================================================================
# ۲) لایه‌ی MongoDB — تمام نوشتن‌ها روی collection «patients»، فیلد visits.{visit_date}
# ==============================================================================

def _mongo_upsert_visit(
    patient_id:   str,
    visit_date:   str,
    entry:        dict[str, Any],
    patient_info: dict[str, Any],
    pull_filter:  dict[str, Any],
) -> dict[str, Any]:
    """
    ورودی:  entry (چیزی که push می‌شود)، pull_filter (کلید dedup)
    خروجی:  {"status": "stored"|"skipped"|"error", ...}
    تریس:   ۱) سند بیمار را upsert می‌کند (patient_info + last_updated)
            ۲) entry قدیمی مشابه (طبق pull_filter) را از visits.{visit_date} حذف می‌کند
            ۳) entry جدید را push می‌کند
    """
    # _id باید همیشه یک نوع داشته باشد؛ وگرنه برای یک بیمار دو سند جدا ساخته می‌شود
    patient_id = str(patient_id)
    date_field = f"visits.{visit_date}"

    try:
        from pymongo import MongoClient
    except Exception as exc:
        # pymongo نصب نیست → پایپ‌لاین متوقف نمی‌شود، فقط ذخیره‌ی مونگو skip می‌شود
        return {"status": "skipped", "reason": f"pymongo unavailable: {exc}"}

    client = MongoClient(os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/"))
    try:
        coll = client[os.getenv("ECHO_MONGO_DB", "echo_pipeline")][os.getenv("ECHO_MONGO_COLLECTION", "patients")]
        coll.update_one({"_id": patient_id},
                        {"$set": {"patient_info": patient_info, "last_updated": datetime.now().isoformat()}},
                        upsert=True)
        coll.update_one({"_id": patient_id}, {"$pull": {date_field: pull_filter}})
        coll.update_one({"_id": patient_id}, {"$push": {date_field: entry}})
    except Exception as exc:
        print(f"MongoDB error: {exc}")
        return {"status": "error", "reason": str(exc)}
    finally:
        client.close()
    return {"status": "stored", "patient_id": patient_id, "visit_date": visit_date}


# ==============================================================================
# ۳) خروجی هر ویدیو (per-view) — setup_video_session → save_reports
# ==============================================================================

def build_public_classification_result(classification_result: dict[str, Any]) -> dict[str, Any]:
    # زیرمجموعه‌ی امنِ classification برای فرانت (بدون مسیرها/فیلدهای داخلی)
    video_path = classification_result.get("video_path")
    return {
        "video_name":  Path(video_path).name if video_path else None,
        "prediction":  classification_result.get("prediction"),
        "source":      classification_result.get("source"),
        "confidence":  classification_result.get("confidence"),
        "class_scores": classification_result.get("class_scores", {}),
    }


def setup_video_session(
    output_root:           Path,
    video_path:            Path,
    patient_id:            str | None,
    classification_result: dict[str, Any],
) -> dict[str, Any]:
    """
    ورودی:  classification_result (prediction قبلاً normalize شده)
    خروجی:  session_paths — تمام مسیرهای لازم برای پردازش یک ویدیو
    ساختار پوشه: output_root / patient_id / YYYY-MM-DD / <view>[_2, _3, ...] / (internal | media | reports)
    در پایان classification.json هم در public/reports نوشته می‌شود.
    """
    internal_root = output_root.expanduser().resolve()
    public_root   = get_public_output_root(internal_root)
    date_name     = datetime.now().strftime("%Y-%m-%d")

    # پوشه‌ی بیمار / تاریخ ویزیت (آینه‌ای در internal و public)
    parent_folder_name = patient_id or (video_path.parent.name if video_path.parent.name != "." else "default")
    internal_date_dir = ensure_dir(internal_root / safe_name(parent_folder_name) / date_name)
    public_date_dir   = ensure_dir(public_root   / safe_name(parent_folder_name) / date_name)

    # پوشه‌ی ویو — اگر همین ویو امروز قبلاً پردازش شده، شماره‌ی افزایشی می‌گیرد (view_2, view_3, ...)
    base_view_name = safe_name(classification_result["prediction"])
    view_name = base_view_name
    index = 2
    while (internal_date_dir / view_name).exists() or (public_date_dir / view_name).exists():
        view_name = f"{base_view_name}_{index}"
        index += 1

    internal_session_dir = ensure_dir(internal_date_dir / view_name)
    public_session_dir   = ensure_dir(public_date_dir / view_name)
    internal_dir         = ensure_dir(internal_session_dir / "internal")

    session_paths = {
        "date_dir":                   internal_date_dir,
        "session_dir":                internal_session_dir,
        "public_session_dir":         public_session_dir,
        "view_name":                  view_name,
        "internal_events_dir":        ensure_dir(internal_dir / "events"),
        "internal_measurements_dir":  ensure_dir(internal_dir / "measurements"),
        "internal_reports_dir":       ensure_dir(internal_dir / "reports"),
        "public_events_dir":          ensure_dir(public_session_dir / "media" / "events"),
        "public_measurements_dir":    ensure_dir(public_session_dir / "media" / "measurements"),
        "public_reports_dir":         ensure_dir(public_session_dir / "reports"),
    }

    write_json(
        build_public_classification_result(classification_result),
        Path(session_paths["public_reports_dir"]) / "classification.json",
    )
    return session_paths


def _build_public_volume_report(
    volume_report: dict[str, Any] | None,
    overlay_destination: Path,
    fields: tuple[str, ...],
) -> dict[str, Any] | None:
    # نسخه‌ی public گزارش حجم (a4c یا lv): فیلدهای انتخابی + کپی تصویر overlay به public
    if not volume_report:
        return None
    overlay_src = volume_report.get("saved_paths", {}).get("overlay_png")
    return {
        **{field: volume_report.get(field) for field in fields},
        "overlay_image": copy_public_file(overlay_src, overlay_destination) if overlay_src else None,
    }


def save_reports(
    *,
    video_path:            Path,
    session_paths:         dict[str, Any],
    patient_id:            str | None,
    patient_config:        dict[str, Any] | None = None,
    classification_result: dict[str, Any],
    events_result:         dict[str, Any],
    internal_rows:         list[dict[str, Any]],
    public_rows:           list[dict[str, Any]],
    a4c_volume_report:     dict[str, Any] | None,
    lv_volume_report:      dict[str, Any] | None = None,
    extra_public_files:    dict[str, str | None] | None = None,
) -> None:
    """
    ورودی:  تمام نتایج پردازش یک ویدیو (extra_public_files: مسیرهای اضافی مثل ecg_plot/scale_debug)
    خروجی روی دیسک: measurements.csv + result.json (public) و نسخه‌ی کامل‌ترشان (internal)
    خروجی مونگو:   یک entry per-view (کلید dedup: view_instance)
    """
    internal_csv_path    = Path(session_paths["internal_reports_dir"]) / "measurement_results_full.csv"
    public_csv_path      = Path(session_paths["public_reports_dir"])   / "measurements.csv"
    internal_report_path = Path(session_paths["internal_reports_dir"]) / "run_report.json"
    public_result_path   = Path(session_paths["public_reports_dir"])   / "result.json"

    # --- مرحله ۱: نوشتن دو CSV (نسخه‌ی کامل داخلی + نسخه‌ی عمومی) ---
    pd.DataFrame(internal_rows).to_csv(internal_csv_path, index=False)
    pd.DataFrame(public_rows).to_csv(public_csv_path, index=False)

    # --- مرحله ۲: نسخه‌ی public گزارش‌های حجم دهلیز/بطن (اگر موجود بودند) ---
    measurements_dir = Path(session_paths["public_measurements_dir"])
    public_a4c = _build_public_volume_report(
        a4c_volume_report, measurements_dir / "a4c_atrial_overlay.png", ("pixels_per_cm", "areas_cm2")
    )
    public_lv = _build_public_volume_report(
        lv_volume_report, measurements_dir / "lv_segmentation_overlay.png", ("pixels_per_cm", "area_cm2")
    )

    # --- مرحله ۳: result.json عمومی (همان چیزی که فرانت مستقیم مصرف می‌کند) ---
    public_result = {
        "patient": {"id": patient_id, **(patient_config or {})},
        "study": {
            "video_name":    video_path.name,
            "processed_at":  datetime.now().isoformat(timespec="seconds"),
            "detected_view": classification_result.get("prediction"),
            "session_dir":   path_for_frontend(session_paths["public_session_dir"]),
            "view_instance": session_paths["view_name"],
        },
        "classification": build_public_classification_result(classification_result),
        "measurements":   public_rows,
        "a4c_volume":     public_a4c,
        "lv_volume":      public_lv,
        "files": {
            "classification_json": path_for_frontend(
                Path(session_paths["public_reports_dir"]) / "classification.json"
            ),
            "measurements_csv": path_for_frontend(public_csv_path),
            "result_json":      path_for_frontend(public_result_path),
            # فایل‌های تصویری اضافی (ecg_plot, scale_debug, ...) — فقط موارد موجود
            **{k: v for k, v in (extra_public_files or {}).items() if v},
        },
    }
    write_json(public_result, public_result_path)

    # --- مرحله ۴: آپسرت در MongoDB — فقط فیلدهایی که فرانت مصرف می‌کند ---
    view_instance = session_paths["view_name"]
    mongo_result = _mongo_upsert_visit(
        patient_id   = public_result["patient"].get("id", "unknown"),
        visit_date   = public_result["study"]["processed_at"].split("T")[0],
        entry        = {
            "view_instance":  view_instance,
            "video_name":     video_path.name,
            "detected_view":  classification_result.get("prediction"),
            "processed_at":   public_result["study"]["processed_at"],
            "measurements":   public_rows,
            "a4c_volume":     public_a4c,
            "lv_volume":      public_lv,
            "classification": public_result["classification"],
            "files":          public_result["files"],
        },
        patient_info = public_result["patient"],
        pull_filter  = {"view_instance": view_instance},
    )

    # --- مرحله ۵ (آخر): run_report.json داخلی — نسخه‌ی کامل برای دیباگ ---
    write_json({
        "video_name": video_path.name,
        "video_path": str(video_path),
        "patient":    {"id": patient_id, **(patient_config or {})},
        "classification": classification_result,
        "events": {
            "event_frames": events_result.get("event_frames", {}),
        },
        "measurements":     internal_rows,
        "a4c_volume":       a4c_volume_report,
        "lv_volume":        lv_volume_report,
        "mongo_store":      mongo_result,
        "public_result_json": path_for_frontend(public_result_path),
    }, internal_report_path)


# ==============================================================================
# ۴) جمع‌بندی چند ویو با منطق فازی — entry مونگو: type="fuzzy_summary"
# ==============================================================================

def aggregate_and_evaluate_fuzzy(
    output_root:       Path,
    patient_id:        str,
    visit_date:        str,
    patient_config:    dict[str, Any],
    rows:              list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    ورودی:  rows (سطرهای اندازه‌گیری همه‌ی ویدیوها)
    خروجی:  fuzzy_result dict (score/category/reasons) یا None اگر هیچ ویویی قابل پردازش نبود
    """
    from fazOres.fuzzy import evaluate_patient, aggregate_patient_rows_for_fuzzy

    date_dir = output_root / safe_name(patient_id) / visit_date
    if not date_dir.exists():
        return None

    # --- مرحله ۱: تجمیع سطرهای خام به دیکشنری ورودی فازی (aggregated_data) ---
    aggregation      = aggregate_patient_rows_for_fuzzy(rows or [], patient_config)
    aggregated_data  = aggregation["aggregated_data"]
    processed_views  = aggregation["processed_views"]

    if not processed_views:
        # هیچ ویوی قابل‌استفاده‌ای پیدا نشد → ارزیابی فازی ممکن نیست
        return None

    agg_folder_name = f"summary_{'&'.join(processed_views)}_{datetime.now().strftime('%H_%M')}"
    agg_dir         = ensure_dir(date_dir / agg_folder_name)

    # --- مرحله ۲: اجرای موتور فازی — امتیاز + دسته‌بندی + دلایل + نمودارها (در agg_dir) ---
    fuzzy_result = evaluate_patient(aggregated_data, patient_name=patient_id, show_plot=agg_dir)
    created_at   = datetime.now().isoformat()

    # --- مرحله ۳: ذخیره‌ی خروجی خام روی دیسک (internal، برای دیباگ/آرشیو) ---
    internal_summary_json = agg_dir / "fuzzy_summary.json"
    write_json({
        "aggregated_input":     aggregated_data,
        "fuzzy_result":         fuzzy_result,
        "processed_views":      processed_views,
        "rows_used_for_fuzzy":  aggregation["rows_used"],
        "timestamp":            created_at,
    }, internal_summary_json)

    # --- مرحله ۴: کپی خروجی‌ها (json + نمودارهای png) به public ---
    public_summary_dir = ensure_dir(
        get_public_output_root(output_root) / safe_name(patient_id) / visit_date / agg_folder_name
    )
    public_media_dir = ensure_dir(public_summary_dir / "media" / "summary")
    public_files: dict[str, Any] = {
        "fuzzy_summary_json": copy_public_file(
            internal_summary_json, public_summary_dir / "reports" / "fuzzy_summary.json"
        ),
        "plots": [
            copied for plot_file in sorted(agg_dir.glob("*.png"))
            if (copied := copy_public_file(plot_file, public_media_dir / plot_file.name))
        ],
    }

    # --- مرحله ۵ (آخر): آپسرت در MongoDB ---
    # فرانت از visit.result (score/category/reasons/plots) و visit.aggregated_data می‌خواند
    _mongo_upsert_visit(
        patient_id   = patient_id,
        visit_date   = visit_date,
        entry        = {
            "type":             "fuzzy_summary",
            "result":           {**fuzzy_result, "plots": public_files["plots"]},
            "aggregated_data":  aggregated_data,
            "files":            public_files,
            "created_at":       created_at,
        },
        patient_info = {"id": patient_id, **(patient_config or {})},
        pull_filter  = {"type": "fuzzy_summary"},
    )

    return fuzzy_result


# ==============================================================================
# ۵) گزارش نهایی (ML + Fuzzy + LLM) — entry مونگو: type="llm_final_report"
#    این entry تنها چیزی است که فرانت به کاربر و پزشک نمایش می‌دهد.
# ==============================================================================

_SEVERITY_FA       = {"LOW": "پایین", "MODERATE": "متوسط", "HIGH": "بالا"}
_FUZZY_TO_SEVERITY = {"normal": "LOW", "mild": "MODERATE", "severe": "HIGH"}
_FUZZY_CAT_FA      = {"Normal": "نرمال", "Mild": "خفیف", "Severe": "شدید"}
_PARAM_LABELS_FA   = {
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


def _build_final_report_data(
    patient_config: dict[str, Any],
    ml_result:      dict[str, Any] | None,
    fuzzy_result:   dict[str, Any] | None,
    echo_rows:      list[dict[str, Any]],
    visit_date:     str,
) -> dict[str, Any]:
    """
    ترکیب ML + Fuzzy + اطلاعات بیمار در یک دیکشنری ساختاریافته.
    فقط فیلدهایی که مصرف‌کننده دارند (پرامپت و HTML گزارش LLM) نگه داشته می‌شوند.
    """
    # شدت کلی = بدترینِ ML و Fuzzy؛ امتیاز کلی = میانگین امتیازهای موجود
    order    = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
    ml_sev   = (ml_result or {}).get("severity", "MODERATE")
    fuzz_cat = (fuzzy_result or {}).get("category", "Normal")
    fuzz_sev = _FUZZY_TO_SEVERITY.get(fuzz_cat.lower(), "MODERATE")
    severity = ml_sev if order.get(ml_sev, 1) >= order.get(fuzz_sev, 1) else fuzz_sev

    scores: list[float] = []
    if ml_result:
        scores.append(float(ml_result.get("combined_score", 50.0)))
    if fuzzy_result and "score" in fuzzy_result:
        scores.append(float(fuzzy_result["score"]))
    score = round(sum(scores) / len(scores), 1) if scores else 50.0

    # اندازه‌گیری‌های اکو — یکتاسازی بر اساس (view, event, name) چون یک پارامتر
    # می‌تواند در چند نما/رویداد جداگانه اندازه‌گیری شود (مثلاً lvid در diastol و sistol)
    seen: set = set()
    echo_measurements: list[dict[str, Any]] = []
    for row in echo_rows:
        mname = row.get("measurement_name", "")
        val   = row.get("length_cm")
        key   = (row.get("detected_view", ""), row.get("event_name", ""), mname)
        if not mname or val is None or key in seen:
            continue
        seen.add(key)
        echo_measurements.append({
            "parameter": mname,
            "label_fa":  _PARAM_LABELS_FA.get(mname, mname),
            "value_cm":  round(float(val), 3),
            "view":      key[0],
            "event":     key[1],
        })

    gender_raw = str(patient_config.get("gender", patient_config.get("sex", ""))).lower()
    return {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "visit_date":   visit_date,
        },
        "patient": {
            "id":     str(patient_config.get("user_id", patient_config.get("id", "N/A"))),
            "age":    patient_config.get("age", "N/A"),
            "gender": "مرد" if gender_raw in ("male", "مرد", "m", "2") else "زن",
        },
        "overall_assessment": {
            "risk_score":  score,
            "severity":    severity,
            "severity_fa": _SEVERITY_FA.get(severity, "متوسط"),
        },
        "echo_analysis": {
            "available":         fuzzy_result is not None,
            "fuzzy_category_fa": _FUZZY_CAT_FA.get(fuzz_cat, fuzz_cat),
            "reasons":           (fuzzy_result or {}).get("reasons", []),
            "echo_measurements": echo_measurements,
        },
        "risk_factors": (ml_result or {}).get("risk_factors", []),
    }


def generate_and_save_final_report(
    output_root:    Path,
    patient_id:     str,
    visit_date:     str,
    patient_config: dict[str, Any],
    ml_result:      dict[str, Any] | None,
    fuzzy_result:   dict[str, Any] | None,
    all_rows:       list[dict[str, Any]],
) -> None:
    """
    ورودی:  تمام نتایج پایپ‌لاین برای یک بیمار/ویزیت (ML + Fuzzy + سطرهای echo)
    خروجی روی دیسک: final_report.json + متن گزارش LLM
    خروجی مونگو:   entry با type="llm_final_report" (فرانت report_text را نمایش می‌دهد)
    """
    # --- مرحله ۱: ساخت داده‌ی ساختاریافته + ذخیره‌ی final_report.json (آرشیو/دیباگ) ---
    report     = _build_final_report_data(patient_config, ml_result, fuzzy_result, all_rows, visit_date)
    report_dir = ensure_dir(output_root / safe_name(patient_id) / visit_date / "final_report")
    write_json(report, report_dir / "final_report.json")

    try:
        # --- مرحله ۲: تولید متن گزارش با LLM — خطا کل پایپ‌لاین را متوقف نمی‌کند ---
        from pipeline.llm_report_generator import LLMReportGenerator

        try:
            llm_report_text = LLMReportGenerator().generate_patient_report(report)
        except Exception as exc:
            # شکست LLM → متن پیش‌فرض جایگزین می‌شود
            print(f"Error generating LLM report: {exc}")
            llm_report_text = "خطا در تولید گزارش."

        # --- مرحله ۳: ذخیره روی دیسک (internal) + کپی به public ---
        llm_text_path = report_dir / "llm_patient_report.txt"
        llm_text_path.write_text(llm_report_text, encoding="utf-8")

        public_report_dir = ensure_dir(
            get_public_output_root(output_root.expanduser().resolve()) / safe_name(patient_id) / visit_date / "final_report"
        )
        public_text_rel = copy_public_file(llm_text_path, public_report_dir / "llm_patient_report.txt")

        # --- مرحله ۴ (آخر): آپسرت در MongoDB ---
        _mongo_upsert_visit(
            patient_id   = patient_id,
            visit_date   = visit_date,
            entry        = {
                "type":            "llm_final_report",
                "generated_at":    datetime.now().isoformat(),
                "report_text":     llm_report_text,
                "files":           {"text": public_text_rel},
            },
            # همان شکل patient_info که save_reports ذخیره می‌کند (weight/height/smoker/...)
            # تا فیلدهایی که فرانت (heart-visualization) مصرف می‌کند overwrite نشوند
            patient_info = {"id": patient_id, **(patient_config or {})},
            pull_filter  = {"type": "llm_final_report"},
        )
    except Exception as exc:
        import traceback
        print(f"    خطا در تولید گزارش LLM: {exc}")
        traceback.print_exc()

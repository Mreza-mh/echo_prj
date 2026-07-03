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

# ریشه‌ی پروژه (echo_prj) — برای محاسبه‌ی مسیر نسبی فایل‌ها نسبت به کل پروژه استفاده می‌شه
PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ==============================================================================
# مسیرها / نگاشت internal ↔ public
# هر خروجی پایپ‌لاین دو نسخه داره: internal (فایل کامل داخلی) و public (نسخه‌ی قابل نمایش به فرانت)
# ==============================================================================

def _public_root_override() -> Path | None:
    # اگه ENV نمونه‌ی .env مسیر عمومی لاراول رو ست کرده باشه (LARAVEL_PUBLIC_RESULT_PATH) همونو برمی‌گردونه
    public_root = os.getenv("LARAVEL_PUBLIC_RESULT_PATH")
    return Path(public_root).expanduser().resolve() if public_root else None


def get_public_output_root(output_root: Path) -> Path:
    # خروجی: اگه override تنظیم شده بود همونو برمی‌گردونه، وگرنه خود output_root
    return _public_root_override() or output_root.expanduser().resolve()


def path_for_frontend(path_value: str | Path | None) -> str | None:
    """
    ورودی:  مسیر مطلق فایل روی دیسک
    خروجی:  مسیر نسبی (برای فرانت/MongoDB) نسبت به public_root override یا ریشه‌ی پروژه
            اگه هیچ‌کدوم match نشد، خود مسیر مطلق برمی‌گرده (fallback)
    """
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    for root in filter(None, [_public_root_override(), PROJECT_ROOT.resolve()]):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return str(path)


def safe_name(value: str) -> str:
    # کاراکترهای غیر الفبایی/عددی رو با _ جایگزین می‌کنه تا اسم پوشه/فایل امن بشه
    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip())
    return safe.strip("_") or "item"


def ensure_dir(path: Path) -> Path:
    # پوشه رو (و والدینش رو) می‌سازه اگه نبود، و خودش رو برمی‌گردونه (برای chain کردن)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(data: dict[str, Any], output_path: Path) -> None:
    # دیکشنری رو با فرمت خوانا (indent=2) و پشتیبانی از فارسی (ensure_ascii=False) ذخیره می‌کنه
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def relative_to_root(path_value: str | Path | None, output_root: Path) -> str | None:
    # خروجی: مسیر نسبی path_value به output_root؛ اگه زیرمجموعه نبود، مسیر مطلق کامل رو برمی‌گردونه
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    try:
        return str(path.relative_to(output_root.resolve()))
    except ValueError:
        return str(path)


def copy_public_file(source: str | Path | None, destination: Path) -> str | None:
    """
    ورودی:  source (مسیر داخلی فایل)، destination (مسیر مقصد در پوشه‌ی public)
    خروجی:  مسیر نسبی قابل استفاده در فرانت، یا None اگه source وجود نداشت
    تریس:   کپی فیزیکی فایل از internal → public انجام می‌شه (نه فقط لینک/رفرنس)
    """
    if not source:
        return None
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source_path, destination)
    return path_for_frontend(destination)


def build_public_classification_result(classification_result: dict[str, Any]) -> dict[str, Any]:
    # ورودی: classification_result کامل | خروجی: زیرمجموعه‌ی امن برای فرانت
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
    ورودی:  classification_result (prediction قبلاً normalize شده)، output_root، patient_id
    خروجی:  session_paths dict — تمام مسیرهای لازم برای یک سشن
    ساختار پوشه: output_root / patient_id / YYYY-MM-DD / <view>[_2, _3, ...] / (internal | media | reports)
    در پایان classification.json هم در public/reports نوشته می‌شه
    """
    internal_root = output_root.expanduser().resolve()
    public_root   = get_public_output_root(internal_root)
    date_name     = datetime.now().strftime("%Y-%m-%d")

    # --- مرحله ۱: پوشه‌ی بیمار / تاریخ ویزیت (آینه‌ای در internal و public) ---
    parent_folder_name = patient_id or (video_path.parent.name if video_path.parent.name != "." else "default")
    internal_date_dir = ensure_dir(internal_root / safe_name(parent_folder_name) / date_name)
    public_date_dir   = ensure_dir(public_root   / safe_name(parent_folder_name) / date_name)

    # --- مرحله ۲: پوشه‌ی ویو — اگه این ویو قبلاً همین روز پردازش شده بود، شماره‌ی افزایشی بهش اضافه می‌شه (view_2, view_3, ...) ---
    base_view_name = safe_name(classification_result["prediction"])
    view_name = base_view_name
    index = 2
    while (internal_date_dir / view_name).exists() or (public_date_dir / view_name).exists():
        view_name = f"{base_view_name}_{index}"
        index += 1

    internal_session_dir = ensure_dir(internal_date_dir / view_name)
    public_session_dir   = ensure_dir(public_date_dir / view_name)
    internal_dir         = ensure_dir(internal_session_dir / "internal")

    # --- مرحله ۳: زیرپوشه‌های نهایی که بقیه‌ی پایپ‌لاین ازش استفاده می‌کنن ---
    session_paths = {
        "internal_root":              internal_root,
        "public_root":                public_root,
        "video_dir":                  internal_date_dir.parent,
        "date_dir":                   internal_date_dir,
        "session_dir":                internal_session_dir,
        "internal_session_dir":       internal_session_dir,
        "public_session_dir":         public_session_dir,
        "public_video_dir":           public_date_dir.parent,
        "public_date_dir":            public_date_dir,
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


# ==============================================================================
# ذخیره‌ی نتایج یک ویدیوی پردازش‌شده (CSV ها + result.json + Mongo)
# ==============================================================================

def _build_public_volume_report(
    volume_report: dict[str, Any] | None,
    overlay_destination: Path,
    fields: tuple[str, ...],
) -> dict[str, Any] | None:
    """
    ورودی:  volume_report (a4c یا lv)، مسیر مقصد تصویر overlay، فیلدهایی که باید نگه داشته بشن
    خروجی:  دیکشنری عمومی شامل فیلدهای انتخابی + مسیر نسبی overlay_image، یا None اگه گزارشی نبود
    """
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
    output_root:           Path,
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
    خروجی روی دیسک: measurement_results_full.csv (internal)، measurements.csv (public)،
                     run_report.json (internal)، result.json (public)
    خروجی جانبی: دیتای public_result در MongoDB هم ذخیره می‌شه
    """
    internal_root = Path(session_paths.get("internal_root", output_root))

    internal_csv_path    = Path(session_paths["internal_reports_dir"]) / "measurement_results_full.csv"
    public_csv_path      = Path(session_paths["public_reports_dir"])   / "measurements.csv"
    internal_report_path = Path(session_paths["internal_reports_dir"]) / "run_report.json"
    public_result_path   = Path(session_paths["public_reports_dir"])   / "result.json"

    # --- مرحله ۱: نوشتن دو CSV (نسخه‌ی کامل داخلی و نسخه‌ی عمومی) ---
    pd.DataFrame(internal_rows).to_csv(internal_csv_path, index=False)
    pd.DataFrame(public_rows).to_csv(public_csv_path, index=False)

    # --- مرحله ۲: ساخت نسخه‌ی عمومی گزارش‌های حجم دهلیز/بطن (اگه موجود بودن) ---
    measurements_dir = Path(session_paths["public_measurements_dir"])
    public_a4c = _build_public_volume_report(
        a4c_volume_report, measurements_dir / "a4c_atrial_overlay.png", ("pixels_per_cm", "areas_cm2")
    )
    public_lv = _build_public_volume_report(
        lv_volume_report, measurements_dir / "lv_segmentation_overlay.png", ("pixels_per_cm", "area_cm2")
    )

    # --- مرحله ۳: ساخت result.json عمومی (چیزی که فرانت مستقیم مصرف می‌کنه) ---
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

    # --- مرحله ۴: آپسرت همین نتیجه در MongoDB (کلید dedup: view_instance) ---
    view_instance = session_paths["view_name"]
    mongo_result = _mongo_upsert_visit(
        patient_id   = public_result["patient"].get("id", "unknown"),
        visit_date   = public_result["study"]["processed_at"].split("T")[0],
        entry        = {
            "view_instance":  view_instance,
            "video_name":     video_path.name,
            "detected_view":  classification_result.get("prediction"),
            "processed_at":   public_result["study"]["processed_at"],
            "session_dir":    public_result["study"]["session_dir"],
            "measurements":   public_rows,
            "a4c_volume":     public_a4c,
            "lv_volume":      public_lv,
            "classification": public_result["classification"],
            "files":          public_result["files"],
            "updated_at":     datetime.now().isoformat(),
        },
        patient_info = public_result["patient"],
        pull_filter  = {"view_instance": view_instance},
    )
    if mongo_result["status"] == "stored":
        mongo_result.update(
            database   = os.getenv("ECHO_MONGO_DB",         "echo_pipeline"),
            collection = os.getenv("ECHO_MONGO_COLLECTION", "patients"),
            view       = view_instance,
        )

    # --- مرحله ۵ (آخر): run_report.json داخلی — نسخه‌ی کامل با تمام فیلدهای داخلی برای دیباگ ---
    write_json({
        "video_name": video_path.name,
        "video_path": str(video_path),
        "patient":    {"id": patient_id, **(patient_config or {})},
        "classification": classification_result,
        "events": {
            "event_frames": events_result.get("event_frames", {}),
            "events_csv":   relative_to_root(events_result.get("events_csv"), internal_root),
        },
        "measurements_csv": relative_to_root(internal_csv_path, internal_root),
        "measurements":     internal_rows,
        "a4c_volume":       a4c_volume_report,
        "lv_volume":        lv_volume_report,
        "mongo_store":      mongo_result,
        "public_result_json": path_for_frontend(public_result_path),
    }, internal_report_path)


# ==============================================================================
# لایه‌ی MongoDB — تمام نوشتن‌ها روی collection «patients» و روی فیلد visits.{visit_date}
# ==============================================================================

def _mongo_upsert_visit(
    patient_id:   str,
    visit_date:   str,
    entry:        dict[str, Any],
    patient_info: dict[str, Any],
    pull_filter:  dict[str, Any],
) -> dict[str, Any]:
    """
    ورودی:  patient_id، visit_date، entry (چیزی که push می‌شه)، patient_info، pull_filter (برای جلوگیری از تکرار)
    خروجی:  {"status": "stored"|"skipped"|"error", ...}
    تریس:   ۱) سند بیمار رو upsert می‌کنه (patient_info + last_updated)
            ۲) اول entry قدیمی مشابه (طبق pull_filter) رو از visits.{visit_date} حذف می‌کنه (dedup)
            ۳) بعد entry جدید رو push می‌کنه
    """
    # _id باید همیشه یک نوع داشته باشه؛ وگرنه دو سند جدا برای یک بیمار ساخته می‌شه
    # (view resultها با id عددیِ patient_config و fuzzy با id رشته‌ایِ CLI می‌اومدن)
    patient_id = str(patient_id)
    date_field = f"visits.{visit_date}"

    try:
        from pymongo import MongoClient
    except Exception as exc:
        # pymongo نصب نیست → پایپ‌لاین متوقف نمی‌شه، فقط اسکیپ می‌شه
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
# گزارش نهایی بیمار (final report) — ترکیب ML + Fuzzy + LLM
# ==============================================================================

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
    خروجی روی دیسک: final_report.json, doctor_report.txt, patient_report.txt + نسخه‌ی متنی/HTML گزارش LLM
    خروجی جانبی: دو entry در MongoDB — type="final_report" (خلاصه) و type="llm_final_report" (گزارش بیمار)
    تریس:   main.py صداش می‌زنه؛ build_final_report → save_report → تولید گزارش LLM
    """
    from ai_service.report_generator import build_final_report, save_report

    # --- مرحله ۱: می‌ره داخل ai_service.report_generator و گزارش ترکیبی نهایی رو می‌سازه ---
    report     = build_final_report(
        patient_config=patient_config, ml_result=ml_result,
        fuzzy_result=fuzzy_result, echo_rows=all_rows, visit_date=visit_date,
    )
    report_dir = ensure_dir(output_root / safe_name(patient_id) / visit_date / "final_report")

    # --- مرحله ۲: گزارش رو روی دیسک ذخیره و خلاصه‌اش رو در Mongo آپسرت می‌کنه (بدون echo_measurements کامل) ---
    save_report(report, report_dir, patient_id, visit_date)
    _mongo_upsert_visit(
        patient_id   = patient_id,
        visit_date   = visit_date,
        entry        = {
            "type":          "final_report",
            "generated_at":  report["meta"]["generated_at"],
            "overall":       {"risk_score": report["overall_assessment"]["risk_score"],
                              "severity":   report["overall_assessment"]["severity"]},
            "ml_analysis":   report.get("ml_analysis", {}),
            "echo_analysis": {k: v for k, v in report.get("echo_analysis", {}).items()
                              if k != "echo_measurements"},
            "risk_factors":  [{"feature": r["feature"], "label": r["label_fa"]}
                              for r in report.get("risk_factors", [])],
            "recommendation": report.get("recommendation", {}),
        },
        patient_info = report.get("patient", {}),
        pull_filter  = {"type": "final_report"},
    )

    # --- مرحله ۳: تولید نسخه‌ی متنی/HTML قابل‌فهم برای بیمار با LLM — خطای این مرحله کل پایپ‌لاین رو fail نمی‌کنه ---
    try:
        from pipeline.llm_report_generator import LLMReportGenerator

        final_report_json_path = report_dir / "final_report.json"
        if not final_report_json_path.exists():
            print(f"Final report not found: {final_report_json_path}")
            return

        with final_report_json_path.open("r", encoding="utf-8") as f:
            final_report_data = json.load(f)

        try:
            generator       = LLMReportGenerator()
            llm_report_text = generator.generate_patient_report(final_report_data)
            html_report     = generator.generate_html_report(llm_report_text, final_report_data)
        except Exception as exc:
            # اگه تولید گزارش با LLM شکست خورد، متن پیش‌فرض جایگزین می‌شه تا کل پایپ‌لاین متوقف نشه
            print(f"Error generating LLM report: {exc}")
            llm_report_text = "خطا در تولید گزارش."
            html_report     = "<html><body><p>خطا در تولید گزارش</p></body></html>"

        llm_text_path = report_dir / "llm_patient_report.txt"
        llm_html_path = report_dir / "patient_report.html"
        llm_text_path.write_text(llm_report_text, encoding="utf-8")
        llm_html_path.write_text(html_report,     encoding="utf-8")

        public_report_dir = ensure_dir(
            get_public_output_root(output_root.expanduser().resolve()) / safe_name(patient_id) / visit_date / "final_report"
        )
        public_text_rel = copy_public_file(llm_text_path, public_report_dir / "llm_patient_report.txt")
        public_html_rel = copy_public_file(llm_html_path, public_report_dir / "patient_report.html")

        _mongo_upsert_visit(
            patient_id   = patient_id,
            visit_date   = visit_date,
            entry        = {
                "type":         "llm_final_report",
                "generated_at": datetime.now().isoformat(),
                "report_text":  llm_report_text,
                "files":        {"html": public_html_rel, "text": public_text_rel},
            },
            patient_info = final_report_data.get("patient", {}),
            pull_filter  = {"type": "llm_final_report"},
        )
    except Exception as exc:
        import traceback
        print(f"    خطا در تولید گزارش LLM: {exc}")
        traceback.print_exc()


# ==============================================================================
# جمع‌بندی چند ویو با منطق فازی (fuzzy) — ورودی نهایی برای ارزیابی ریسک قلبی
# ==============================================================================

def aggregate_and_evaluate_fuzzy(
    output_root:       Path,
    patient_id:        str,
    visit_date:        str,
    patient_config:    dict[str, Any],
    rows:              list[dict[str, Any]] | None = None,
    summary_csv_path:  Path | None = None,
) -> dict[str, Any] | None:
    """
    ورودی:  rows (سطرهای همه‌ی ویدیوها) یا summary_csv_path (اگه rows داده نشده بود از روی CSV می‌خونه)
    خروجی:  fuzzy_result dict (شامل score/category/reasons/llm_prompt) یا None اگه هیچ ویویی پردازش نشده بود
    """
    from fazOres.fuzzy import evaluate_patient, aggregate_patient_rows_for_fuzzy

    date_dir = output_root / safe_name(patient_id) / visit_date
    if not date_dir.exists():
        return None

    # --- مرحله ۱: منبع سطرها رو مشخص می‌کنیم — یا مستقیم rows، یا خوندن از CSV ---
    source_rows = rows
    if source_rows is None and summary_csv_path and summary_csv_path.exists():
        try:
            source_rows = pd.read_csv(summary_csv_path).to_dict(orient="records")
        except Exception as exc:
            print(f"Error reading summary CSV for aggregation: {exc}")
            source_rows = []
    elif source_rows is None:
        source_rows = []

    # --- مرحله ۲: می‌ره داخل fazOres.fuzzy و سطرهای خام رو به یک دیکشنری تجمیعی (aggregated_data) تبدیل می‌کنه ---
    aggregation      = aggregate_patient_rows_for_fuzzy(source_rows, patient_config)
    aggregated_data  = aggregation["aggregated_data"]
    processed_views  = aggregation["processed_views"]
    rows_used        = aggregation["rows_used"]

    if not processed_views:
        # هیچ ویوی قابل‌استفاده‌ای پیدا نشد → نمی‌شه ارزیابی فازی انجام داد
        return None

    views_str      = "&".join(processed_views)
    agg_folder_name = f"summary_{views_str}_{datetime.now().strftime('%H_%M')}"
    agg_dir        = ensure_dir(date_dir / agg_folder_name)

    # --- مرحله ۳: اجرای موتور فازی — امتیاز ریسک + دسته‌بندی + دلایل + نمودارها (در agg_dir ذخیره می‌شن) ---
    fuzzy_result = evaluate_patient(aggregated_data, patient_name=patient_id, show_plot=agg_dir)

    # --- مرحله ۴: ساخت پرامپت آماده برای LLM بر اساس نتیجه‌ی فازی (بعداً توسط report_generator مصرف می‌شه) ---
    llm_prompt = (
        "[SYSTEM DIRECTIVE FOR LLM]\n"
        "You are an expert cardiologist assistant. Below is the fuzzy logic evaluation of a patient's echocardiography.\n"
        "Please generate a patient-friendly, easy-to-understand but clinically accurate medical report in Persian.\n\n"
        f"[PATIENT DATA]\n"
        f"- ID: {patient_id}\n"
        f"- Gender: {aggregated_data.get('gender', 'Unknown')}\n"
        f"- Weight: {aggregated_data.get('weight', 'N/A')} kg, Height: {aggregated_data.get('height', 'N/A')} cm\n\n"
        f"[FUZZY LOGIC RESULTS]\n"
        f"- Final Risk Score: {fuzzy_result.get('score', 0):.1f} / 100\n"
        f"- Risk Category: {fuzzy_result.get('category', 'Unknown')} "
        f"(Categories are: Normal [0-35], Mild Risk [35-65], Severe Risk [65-100])\n\n"
        "[ABNORMAL FINDINGS (Reasons for Risk)]\n" +
        ("\n".join(f"- {r}" for r in fuzzy_result.get("reasons", [])) or "- All parameters are within normal ranges.") +
        "\n\n[CONTEXT FOR LLM]\n"
        "- 'processed' parameters mean the value was divided by the Body Surface Area (BSA) to normalize for body size.\n"
        f"- Explain to the patient what \"{fuzzy_result.get('category', 'Unknown')}\" means for them.\n"
        "- If risk is Mild, advise routine follow-up and lifestyle changes.\n"
        "- If risk is Severe, advise urgent consultation with a cardiologist.\n"
        "- Mention which specific parts of the heart are enlarged or thickened based on the findings above.\n"
    )

    created_at = datetime.now().isoformat()
    fuzzy_result["llm_prompt"] = llm_prompt

    # --- مرحله ۵: ذخیره‌ی خروجی خام روی دیسک (internal) ---
    summary_payload = {
        "aggregated_input":      aggregated_data,
        "fuzzy_result":          fuzzy_result,
        "processed_views":       processed_views,
        "rows_used_for_fuzzy":   rows_used,
        "timestamp":             created_at,
    }

    internal_summary_json = agg_dir / "fuzzy_summary.json"
    internal_report_txt   = agg_dir / "fuzzy_report.txt"
    write_json(summary_payload, internal_summary_json)
    internal_report_txt.write_text(llm_prompt, encoding="utf-8")

    # --- مرحله ۶: کپی خروجی‌ها (json/txt/نمودارهای png) به پوشه‌ی public ---
    public_root       = get_public_output_root(output_root)
    public_summary_dir = ensure_dir(public_root / safe_name(patient_id) / visit_date / agg_folder_name)
    public_reports_dir = ensure_dir(public_summary_dir / "reports")
    public_media_dir   = ensure_dir(public_summary_dir / "media" / "summary")

    public_files: dict[str, Any] = {
        "fuzzy_summary_json": copy_public_file(internal_summary_json, public_reports_dir / "fuzzy_summary.json"),
        "fuzzy_report_txt":   copy_public_file(internal_report_txt,   public_reports_dir / "fuzzy_report.txt"),
        "plots": [
            copied for plot_file in sorted(agg_dir.glob("*.png"))
            if (copied := copy_public_file(plot_file, public_media_dir / plot_file.name))
        ],
    }

    # --- مرحله ۷ (آخر): ثبت خلاصه‌ی نتیجه‌ی فازی در MongoDB (type="fuzzy_summary") ---
    compact_fuzzy = {k: v for k, v in fuzzy_result.items() if k != "llm_prompt"}
    # نمودارهای فازی داخل result هم قرار می‌گیرند چون فرانت از visit.result.plots می‌خواند
    compact_fuzzy["plots"] = public_files["plots"]
    summary_entry = {
        "type":             "fuzzy_summary",
        "folder_name":      agg_folder_name,
        "result":           compact_fuzzy,
        "processed_views":  processed_views,
        "aggregated_data":  aggregated_data,
        "files":            public_files,
        "created_at":       created_at,
    }
    _mongo_upsert_visit(
        patient_id   = patient_id,
        visit_date   = visit_date,
        entry        = summary_entry,
        patient_info = {"id": patient_id, **(patient_config or {})},
        pull_filter  = {"type": "fuzzy_summary"},
    )

    return fuzzy_result

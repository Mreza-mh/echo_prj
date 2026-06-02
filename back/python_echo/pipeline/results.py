"""این فایل مسیرهای خروجی، کپی فایل‌های عمومی و ذخیره نتیجه عمومی در Mongo را ساده و یک‌جا مدیریت می‌کند."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import Any
from dotenv import load_dotenv
import pandas as pd

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_public_output_root(output_root: Path) -> Path:
    public_root = os.getenv("LARAVEL_PUBLIC_RESULT_PATH")
    if public_root:
        return Path(public_root).expanduser().resolve()
    return output_root.expanduser().resolve()


def path_for_frontend(path_value: str | Path | None) -> str | None:
    """
    تبدیل مسیر مطلق به مسیر نسبی برای استفاده در فرانت‌اند و MongoDB.
    
    مثال:
        ورودی: C:/Users/.../public/echos/2/2026-06-02/a4c/media/events/End_Diastol.jpg
        خروجی: 2/2026-06-02/a4c/media/events/End_Diastol.jpg
    """
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()

    public_root = os.getenv("LARAVEL_PUBLIC_RESULT_PATH")
    if public_root:
        try:
            # تبدیل به مسیر نسبی نسبت به public_root
            relative = path.relative_to(Path(public_root).expanduser().resolve())
            return relative.as_posix()
        except Exception:
            pass

    try:
        return path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return str(path)


def safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip())
    return safe.strip("_") or "item"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(data: dict[str, Any], output_path: Path) -> None:
    import json

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def relative_to_root(path_value: str | Path | None, output_root: Path) -> str | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    try:
        return str(path.relative_to(output_root.resolve()))
    except Exception:
        return str(path)


def build_session_paths(
    output_root: Path,
    video_path: Path,
    detected_view: str,
    patient_id: str | None = None,
) -> dict[str, Path | str]:
    internal_root = output_root.expanduser().resolve()
    public_root = get_public_output_root(internal_root)

    date_name = datetime.now().strftime("%Y-%m-%d")
    # اگر ورودی پوشه باشد، اسم پوشه پدر ویدیو را به عنوان شناسنامه در نظر می‌گیریم
    # اما فعلاً برای حفظ سازگاری از safe_name(video_path.stem) استفاده می‌کنیم
    # در main.py این مورد را دقیق‌تر مدیریت می‌کنیم
    
    parent_folder_name = patient_id or (video_path.parent.name if video_path.parent.name != "." else "default")
    internal_video_dir = ensure_dir(internal_root / safe_name(parent_folder_name))
    public_video_dir = ensure_dir(public_root / safe_name(parent_folder_name))
    internal_date_dir = ensure_dir(internal_video_dir / date_name)
    public_date_dir = ensure_dir(public_video_dir / date_name)

    base_view_name = safe_name(detected_view)
    view_name = base_view_name
    index = 2
    while (internal_date_dir / view_name).exists() or (public_date_dir / view_name).exists():
        view_name = f"{base_view_name}_{index}"
        index += 1

    internal_session_dir = ensure_dir(internal_date_dir / view_name)
    public_session_dir = ensure_dir(public_date_dir / view_name)
    internal_dir = ensure_dir(internal_session_dir / "internal")
    # حذف "public" اضافی - فایل‌ها مستقیم در view_name ذخیره می‌شوند
    public_dir = public_session_dir

    return {
        "internal_root": internal_root,
        "public_root": public_root,
        "video_dir": internal_video_dir,
        "date_dir": internal_date_dir,
        "session_dir": internal_session_dir,
        "internal_session_dir": internal_session_dir,
        "public_session_dir": public_session_dir,
        "public_video_dir": public_video_dir,
        "public_date_dir": public_date_dir,
        "view_name": view_name,
        "internal_events_dir": ensure_dir(internal_dir / "events"),
        "internal_measurements_dir": ensure_dir(internal_dir / "measurements"),
        "internal_reports_dir": ensure_dir(internal_dir / "reports"),
        "public_events_dir": ensure_dir(public_dir / "media" / "events"),
        "public_measurements_dir": ensure_dir(public_dir / "media" / "measurements"),
        "public_reports_dir": ensure_dir(public_dir / "reports"),
    }


def copy_public_file(source: str | Path | None, destination: Path, output_root: Path) -> str | None:
    """
    کپی یک فایل از مسیر مبدأ (internal) به مسیر مقصد (public) و بازگشت مسیر نسبی.
    
    Args:
        source: مسیر فایل مبدأ (مثلاً فایل در پوشه internal)
        destination: مسیر مقصد کامل (مثلاً در public_root/...)
        output_root: پوشه ریشه (استفاده نمی‌شود، برای سازگاری نگه داشته شده)
    
    Returns:
        مسیر نسبی فایل نسبت به public_root (برای ذخیره در MongoDB و استفاده در API)
        مثال: "2/2026-06-02/a4c/media/events/End_Diastol.jpg"
    """
    if not source:
        return None
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        return None
    
    # ایجاد پوشه مقصد و کپی فایل
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source_path, destination)
    
    # بازگشت مسیر نسبی برای استفاده در فرانت‌اند
    return path_for_frontend(destination)


def save_public_result_to_mongo(document: dict[str, Any]) -> dict[str, Any]:
    mongo_uri = os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/")
    
    try:
        from pymongo import MongoClient
    except Exception as exc:
        return {"status": "skipped", "reason": f"pymongo_unavailable: {exc}"}

    database_name = os.getenv("ECHO_MONGO_DB", "echo_pipeline")
    collection_name = os.getenv("ECHO_MONGO_COLLECTION", "patients")
    
    # استخراج اطلاعات پایه
    patient_info = document.get("patient", {})
    patient_id = patient_info.get("id", "unknown")
    
    # استخراج تاریخ (مثلاً 2026-05-16)
    processed_at = document.get("study", {}).get("processed_at", "")
    visit_date = processed_at.split("T")[0] if "T" in processed_at else datetime.now().strftime("%Y-%m-%d")
    
    view_instance = document.get("study", {}).get("view_instance", "unknown")

    # ساختار داده برای این نمای خاص
    view_result = {
        "view_instance": view_instance,
        "video_name": document.get("study", {}).get("video_name"),
        "detected_view": document.get("study", {}).get("detected_view"),
        "processed_at": processed_at,
        "session_dir": document.get("study", {}).get("session_dir"),
        "measurements": document.get("measurements", []),
        "a4c_volume": document.get("a4c_volume"),
        "lv_volume": document.get("lv_volume"),
        "classification": document.get("classification"),
        "files": document.get("files", {}),
        "updated_at": datetime.now().isoformat()
    }

    client = MongoClient(mongo_uri)
    try:
        collection = client[database_name][collection_name]
        
        # 1. ابتدا اطلاعات کلی بیمار را به‌روزرسانی می‌کنیم (Upsert Patient)
        collection.update_one(
            {"_id": patient_id},
            {
                "$set": {
                    "patient_info": patient_info,
                    "last_updated": datetime.now().isoformat()
                }
            },
            upsert=True
        )
        
        # 2. حذف نسخه قدیمی همین نما در همین تاریخ (اگر وجود داشته باشد) برای جلوگیری از تکرار
        date_field = f"visits.{visit_date}"
        collection.update_one(
            {"_id": patient_id},
            {"$pull": {date_field: {"view_instance": view_instance}}}
        )
        
        # 3. اضافه کردن نتیجه جدید به لیست نماهای آن تاریخ
        collection.update_one(
            {"_id": patient_id},
            {"$push": {date_field: view_result}}
        )
        
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}
    finally:
        client.close()

    return {
        "status": "stored", 
        "database": database_name, 
        "collection": collection_name, 
        "patient_id": patient_id,
        "visit_date": visit_date,
        "view": view_instance
    }

# //az in

def generate_final_patient_report(
    output_root: Path,
    patient_id: str,
    visit_date: str,
    final_report_json_path: Path,
) -> dict[str, Any] | None:
    """
    تولید گزارش نهایی برای بیمار با استفاده از LLM و ذخیره در MongoDB
    
    این تابع:
    1. فایل final_report.json را می‌خواند
    2. از LLM برای تولید متن دوستانه استفاده می‌کند
    3. یک فایل HTML زیبا تولید می‌کند
    4. همه چیز را در MongoDB ذخیره می‌کند
    
    ورودی:
        output_root: پوشه ریشه خروجی
        patient_id: شناسه بیمار
        visit_date: تاریخ ویزیت
        final_report_json_path: مسیر فایل final_report.json
    
    خروجی:
        دیکشنری حاوی مسیرهای فایل‌های تولید شده و وضعیت ذخیره در MongoDB
    """
    from pipeline.llm_report_generator import LLMReportGenerator
    import json
    
    if not final_report_json_path.exists():
        print(f"Final report not found: {final_report_json_path}")
        return None
    
    # خواندن داده‌های گزارش نهایی
    with final_report_json_path.open("r", encoding="utf-8") as f:
        final_report_data = json.load(f)
    
    # تولید گزارش با LLM
    try:
        generator = LLMReportGenerator()
        llm_report_text = generator.generate_patient_report(final_report_data)
        
        if not llm_report_text:
            print("LLM failed to generate report, using fallback")
            llm_report_text = "گزارش در دسترس نیست. لطفاً با پزشک مشورت کنید."
        
        # تولید HTML
        html_report = generator.generate_html_report(
            llm_report=llm_report_text,
            final_report_data=final_report_data
        )
        
    except Exception as e:
        print(f"Error generating LLM report: {e}")
        llm_report_text = "خطا در تولید گزارش."
        html_report = "<html><body><p>خطا در تولید گزارش</p></body></html>"
    
    # تعیین مسیرهای ذخیره
    internal_root = output_root.expanduser().resolve()
    public_root = get_public_output_root(internal_root)
    
    patient_dir = internal_root / safe_name(patient_id)
    date_dir = patient_dir / visit_date
    final_report_dir = ensure_dir(date_dir / "final_report")
    
    # ذخیره فایل‌های متنی و HTML در internal
    llm_text_path = final_report_dir / "llm_patient_report.txt"
    llm_html_path = final_report_dir / "patient_report.html"
    
    with llm_text_path.open("w", encoding="utf-8") as f:
        f.write(llm_report_text)
    
    with llm_html_path.open("w", encoding="utf-8") as f:
        f.write(html_report)
    
    # کپی به پوشه public
    public_patient_dir = public_root / safe_name(patient_id) / visit_date / "final_report"
    ensure_dir(public_patient_dir)
    
    public_text_path = public_patient_dir / "llm_patient_report.txt"
    public_html_path = public_patient_dir / "patient_report.html"
    
    public_text_relative = copy_public_file(llm_text_path, public_text_path, public_root)
    public_html_relative = copy_public_file(llm_html_path, public_html_path, public_root)
    
    # ذخیره در MongoDB
    mongo_uri = os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/")
    
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri)
        db = client[os.getenv("ECHO_MONGO_DB", "echo_pipeline")]
        coll = db[os.getenv("ECHO_MONGO_COLLECTION", "patients")]
        
        # ساخت entry برای MongoDB
        llm_report_entry = {
            "type": "llm_final_report",
            "generated_at": datetime.now().isoformat(),
            "report_text": llm_report_text,
            "files": {
                "html": public_html_relative,
                "text": public_text_relative
            }
        }
        
        # به‌روزرسانی document بیمار
        patient_info = final_report_data.get("patient", {})
        date_field = f"visits.{visit_date}"
        
        coll.update_one(
            {"_id": patient_id},
            {
                "$set": {
                    "patient_info": patient_info,
                    "last_updated": datetime.now().isoformat(),
                }
            },
            upsert=True,
        )
        
        # حذف گزارش قدیمی (اگر وجود دارد)
        coll.update_one(
            {"_id": patient_id},
            {"$pull": {date_field: {"type": "llm_final_report"}}},
        )
        
        # اضافه کردن گزارش جدید
        coll.update_one(
            {"_id": patient_id},
            {"$push": {date_field: llm_report_entry}}
        )
        
        client.close()
        
        mongo_status = {
            "status": "success",
            "patient_id": patient_id,
            "visit_date": visit_date
        }
        
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")
        mongo_status = {"status": "error", "message": str(e)}
    
    return {
        "llm_report_text": llm_report_text,
        "internal_files": {
            "text": str(llm_text_path),
            "html": str(llm_html_path)
        },
        "public_files": {
            "text": public_text_relative,
            "html": public_html_relative
        },
        "mongodb": mongo_status
    }


def aggregate_and_evaluate_fuzzy(
    output_root: Path,
    patient_id: str,
    visit_date: str,
    patient_config: dict[str, Any],
    rows: list[dict[str, Any]] | None = None,
    summary_csv_path: Path | None = None,
) -> dict[str, Any] | None:
    """
    تجمیع تمام نتایج اندازه‌گیری‌های یک بیمار در یک تاریخ مشخص و اجرای ارزیابی فازی.

    مراحل:
      ۱) پیمایش پوشه تاریخ (2026-05-18) و خواندن run_report.json از هر نما
      ۲) تجمیع مقادیر اندازه‌گیری‌ها با نگاشت param_map
         - پارامترهای خطی (ivs, lvid, aorta, ...) از measurements استخراج می‌شوند
         - حجم دهلیزها (la_volume, ra_volume) از a4c_volume.areas_cm2
         - حجم بطن چپ (lv_edv) از lv_volume.area_cm2
      ۳) اجرای evaluate_patient با داده‌های تجمیع‌شده
      ۴) تولید پرامپت برای LLM و ذخیره نتایج در پوشه summary

    ورودی:
        output_root   : پوشه ریشه خروجی (C:/.../result)
        patient_id    : شناسه بیمار ("404445623")
        visit_date    : تاریخ ویزیت ("2026-05-18")
        patient_config: اطلاعات بیمار از config.json + id پوشه

    خروجی (از لاگ واقعی):
        {
            "score": 0.0,
            "category": "Normal",
            "reasons": [],
            "text": "Score: 0.0/100 | Category: Normal\nReasons:\n  - All normal.",
            "llm_prompt": "..."
        }
        یا None اگر date_dir وجود نداشته باشد یا هیچ نمایی پردازش نشده باشد
    
    توجه مهم از لاگ:
        - "rv_base" در param_map نیست ← اندازه‌گیری‌های rv_base نادیده گرفته می‌شوند
        - "lvid", "aorta", "aortic_root" length_cm ندارند (None) ← نادیده گرفته می‌شوند
        - فقط "ivs" با موفقیت استخراج شد: ivs → ivs_thickness = 0.8371
    """
    from fazOres.fuzzy import evaluate_patient, aggregate_patient_rows_for_fuzzy
    from datetime import datetime

    patient_dir = output_root / safe_name(patient_id)
    date_dir = patient_dir / visit_date

    if not date_dir.exists():
        return None

    source_rows = rows
    if source_rows is None and summary_csv_path and summary_csv_path.exists():
        try:
            source_rows = pd.read_csv(summary_csv_path).to_dict(orient="records")
        except Exception as e:
            print(f"Error reading summary CSV for aggregation: {e}")
            source_rows = []
    elif source_rows is None:
        source_rows = []

    aggregation = aggregate_patient_rows_for_fuzzy(source_rows, patient_config)
    aggregated_data = aggregation["aggregated_data"]
    processed_views = aggregation["processed_views"]
    rows_used = aggregation["rows_used"]

    if not processed_views:
        return None

    views_str = "&".join(processed_views)
    time_str = datetime.now().strftime("%H_%M")
    agg_folder_name = f"summary_{views_str}_{time_str}"
    agg_dir = ensure_dir(date_dir / agg_folder_name)

    fuzzy_result = evaluate_patient(
        aggregated_data,
        patient_name=patient_id,
        show_plot=agg_dir
    )

    llm_prompt = f"""
    [SYSTEM DIRECTIVE FOR LLM]
    You are an expert cardiologist assistant. Below is the fuzzy logic evaluation of a patient's echocardiography.
    Please generate a patient-friendly, easy-to-understand but clinically accurate medical report in Persian.
    
    [PATIENT DATA]
    - ID: {patient_id}
    - Gender: {aggregated_data.get('gender', 'Unknown')}
    - Weight: {aggregated_data.get('weight', 'N/A')} kg, Height: {aggregated_data.get('height', 'N/A')} cm
    
    [FUZZY LOGIC RESULTS]
    - Final Risk Score: {fuzzy_result.get('score', 0):.1f} / 100
    - Risk Category: {fuzzy_result.get('category', 'Unknown')} (Categories are: Normal [0-35], Mild Risk [35-65], Severe Risk [65-100])
    
    [ABNORMAL FINDINGS (Reasons for Risk)]
    {chr(10).join(['- ' + r for r in fuzzy_result.get('reasons', [])]) if fuzzy_result.get('reasons') else '- All parameters are within normal ranges.'}
    
    [CONTEXT FOR LLM]
    - 'processed' parameters mean the value was divided by the Body Surface Area (BSA) to normalize it for the patient's body size.
    - Explain to the patient what "{fuzzy_result.get('category', 'Unknown')}" means for them.
    - If risk is Mild, advise routine follow-up and lifestyle changes.
    - If risk is Severe, advise urgent consultation with a cardiologist.
    - Mention which specific parts of the heart are enlarged or thickened based on the findings above.
    """

    created_at = datetime.now().isoformat()
    fuzzy_result["llm_prompt"] = llm_prompt
    summary_payload = {
        "aggregated_input": aggregated_data,
        "fuzzy_result": fuzzy_result,
        "processed_views": processed_views,
        "rows_used_for_fuzzy": rows_used,
        "timestamp": created_at,
    }

    internal_summary_json = agg_dir / "fuzzy_summary.json"
    internal_report_txt = agg_dir / "fuzzy_report.txt"
    write_json(summary_payload, internal_summary_json)

    with internal_report_txt.open("w", encoding="utf-8") as f:
        f.write(llm_prompt)

    public_root = get_public_output_root(output_root)
    # حذف "public" اضافی - فایل‌ها مستقیم در agg_folder_name ذخیره می‌شوند
    public_summary_dir = ensure_dir(
        public_root / safe_name(patient_id) / visit_date / agg_folder_name
    )
    public_reports_dir = ensure_dir(public_summary_dir / "reports")
    public_media_dir = ensure_dir(public_summary_dir / "media" / "summary")

    public_files: dict[str, Any] = {
        "fuzzy_summary_json": copy_public_file(
            internal_summary_json,
            public_reports_dir / "fuzzy_summary.json",
            public_root,
        ),
        "fuzzy_report_txt": copy_public_file(
            internal_report_txt,
            public_reports_dir / "fuzzy_report.txt",
            public_root,
        ),
        "plots": [],
    }
    for plot_file in sorted(agg_dir.glob("*.png")):
        copied_plot = copy_public_file(plot_file, public_media_dir / plot_file.name, public_root)
        if copied_plot:
            public_files["plots"].append(copied_plot)

    compact_fuzzy_result = {
        key: value for key, value in fuzzy_result.items() if key != "llm_prompt"
    }
    mongo_uri = os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/")
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri)
        db = client[os.getenv("ECHO_MONGO_DB", "echo_pipeline")]
        coll = db[os.getenv("ECHO_MONGO_COLLECTION", "patients")]

        summary_entry = {
            "type": "fuzzy_summary",
            "folder_name": agg_folder_name,
            "result": compact_fuzzy_result,
            "processed_views": processed_views,
            "aggregated_data": aggregated_data,
            "files": public_files,
            "created_at": created_at,
        }

        patient_info = {
            "id": patient_id,
            **(patient_config or {}),
        }
        date_field = f"visits.{visit_date}"
        coll.update_one(
            {"_id": patient_id},
            {
                "$set": {
                    "patient_info": patient_info,
                    "last_updated": datetime.now().isoformat(),
                }
            },
            upsert=True,
        )
        coll.update_one(
            {"_id": patient_id},
            {"$pull": {date_field: {"type": "fuzzy_summary"}}},
        )
        coll.update_one(
            {"_id": patient_id},
            {"$push": {date_field: summary_entry}}
        )
        client.close()
    except Exception as e:
        print(f"Error updating mongo with fuzzy summary: {e}")

    return fuzzy_result
    

from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from pipeline.config import CLASSIFIER_MODEL, RESULT_DIR, VIEW_PIPELINES
from pipeline.measurement import inference_2d as measurement_module
from pipeline.paths import patch_sys_argv_from_windows_command_line, resolve_video_path
from pipeline.processing import process_video
from pipeline.results import aggregate_and_evaluate_fuzzy, ensure_dir, safe_name
import os
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ai_service.mongo_reader import get_patient_config
from ai_service.ml_predictor import MLRiskPredictor
from ai_service.report_generator import build_final_report, save_report

BASE_DIR = Path(__file__).resolve().parent

# ── ML Predictor (یک‌بار لود می‌شه و برای همه بیماران استفاده می‌شه) ─────────
_ml_predictor: MLRiskPredictor | None = None


def get_ml_predictor() -> MLRiskPredictor:
    """Lazy singleton — مدل‌ها فقط یک‌بار از دیسک بارگذاری می‌شوند"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLRiskPredictor()
    return _ml_predictor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Echo pipeline")
    parser.add_argument("video", help="Input video path.")
    parser.add_argument("--output-root", default=str(RESULT_DIR), help="Root folder for outputs.")
    parser.add_argument("--view", choices=sorted(VIEW_PIPELINES.keys()), default=None,
                        help="Force the view and skip classifier.")
    parser.add_argument("--classifier-model",
                        default=str(CLASSIFIER_MODEL) if CLASSIFIER_MODEL.exists() else None,
                        help="Path to view classifier model.")
    parser.add_argument("--classifier-samples", type=int, default=8,
                        help="Number of sampled frames for classification.")
    parser.add_argument("--one-frame-repeat", type=int, default=8,
                        help="How many times the selected frame should repeat in the temporary AVI.")
    parser.add_argument("--device", default=None, help="Torch device for measurement models.")
    parser.add_argument("--default-pixels-per-cm", type=float, default=12.0,
                        help="Fallback scale when automatic ruler detection fails.")
    parser.add_argument("--ml-only", action="store_true",
                        help="فقط ML prediction اجرا شود، بدون پردازش ویدیو.")
    return parser


def run_ml_analysis(patient_config: dict) -> dict | None:
    """
    اجرای تحلیل ML روی اطلاعات بیمار از MongoDB.
    Features را از patient_config استخراج و BMI را محاسبه می‌کند.
    """
    print("\n اجرای تحلیل هوش مصنوعی (ML)...")
    try:
        predictor   = get_ml_predictor()
        ml_result   = predictor.predict(patient_config)

        # بررسی اینکه آیا خطا در مدل‌ها وجود دارد
        if "error" in ml_result.get("hd_result", {}) or "error" in ml_result.get("cv_result", {}):
            print("     خطا در بارگذاری مدل‌ها:")
            if "error" in ml_result.get("hd_result", {}):
                print(f"      - HD: {ml_result['hd_result']['error']}")
            if "error" in ml_result.get("cv_result", {}):
                print(f"      - CV: {ml_result['cv_result']['error']}")
            return None

        sev = ml_result.get("severity", "?")
        score = ml_result.get("combined_score", 0)
        bmi = ml_result.get("bmi")

        print(f"    HD_LogisticRegression : {ml_result['hd_result']['probability_pct']:.1f}%")
        print(f"    CV_CatBoost           : {ml_result['cv_result']['probability_pct']:.1f}%")
        print(f"    امتیاز ترکیبی        : {score:.1f}/100  |  شدت: {sev}")
        if bmi:
            print(f"    BMI محاسبه‌شده       : {bmi:.1f} kg/m²")

        rf_count = len(ml_result.get("risk_factors", []))
        if rf_count:
            print(f"     عوامل خطر شناسایی‌شده: {rf_count} مورد")

        return ml_result

    except Exception as exc:
        print(f"    خطا در ML analysis: {exc}")
        import traceback
        traceback.print_exc()
        return None


def generate_and_save_final_report(
    output_root:    Path,
    patient_id:     str,
    visit_date:     str,
    patient_config: dict,
    ml_result:      dict | None,
    fuzzy_result:   dict | None,
    all_rows:       list[dict],
) -> None:
    """
    تولید گزارش جامع نهایی (ML + Fuzzy + Echo) و ذخیره در دیسک و MongoDB.
    """
    print("\n تولید گزارش نهایی...")

    report = build_final_report(
        patient_config = patient_config,
        ml_result      = ml_result,
        fuzzy_result   = fuzzy_result,
        echo_rows      = all_rows,
        visit_date     = visit_date,
    )

    # مسیر ذخیره
    report_dir = ensure_dir(output_root / safe_name(patient_id) / visit_date / "final_report")
    saved_paths = save_report(report, report_dir, patient_id, visit_date)

    sev    = report["overall_assessment"]["severity"]
    score  = report["overall_assessment"]["risk_score"]
    emoji  = report["overall_assessment"]["severity_emoji"]
    urgency = report["recommendation"]["urgency"]

    print(f"    ریسک نهایی : {emoji} {sev}  (امتیاز: {score}/100)")
    print(f"    فوریت      : {urgency}")
    print(f"    گزارش پزشک : {saved_paths.get('doctor_txt', '')}")
    print(f"    گزارش بیمار: {saved_paths.get('patient_txt', '')}")
    print(f"    JSON کامل  : {saved_paths.get('json', '')}")

    # ذخیره در MongoDB (در کنار نتایج قبلی)
    _save_report_to_mongo(patient_id, visit_date, report)

    # نمایش گزارش بیمار در ترمینال (اختیاری)
    print("\n" + "─" * 65)
    print(report.get("patient_report", ""))
    print("─" * 65)
    
    # تولید گزارش LLM برای بیمار
    print("\n تولید گزارش هوشمند برای بیمار...")
    try:
        from pipeline.results import generate_final_patient_report
        final_report_json = report_dir / "final_report.json"
        
        llm_result = generate_final_patient_report(
            output_root=output_root,
            patient_id=patient_id,
            visit_date=visit_date,
            final_report_json_path=final_report_json
        )
        
        if llm_result:
            print(f"    گزارش LLM تولید شد")
            print(f"    HTML: {llm_result['public_files']['html']}")
            print(f"    Text: {llm_result['public_files']['text']}")
            
            # نمایش متن گزارش در ترمینال
            print("\n" + "═" * 65)
            print("گزارش هوشمند برای بیمار:")
            print("═" * 65)
            print(llm_result['llm_report_text'])
            print("═" * 65)
        else:
            print("     خطا در تولید گزارش LLM")
            
    except Exception as exc:
        print(f"    خطا در تولید گزارش LLM: {exc}")
        import traceback
        traceback.print_exc()


def _save_report_to_mongo(patient_id: str, visit_date: str, report: dict) -> None:
    """ذخیره گزارش نهایی در MongoDB"""
    mongo_uri = os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/")
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri)
        db   = client[os.getenv("ECHO_MONGO_DB", "echo_pipeline")]
        coll = db[os.getenv("ECHO_MONGO_COLLECTION", "patients")]

        # خلاصه قابل ذخیره (بدون رشته‌های طولانی report)
        mongo_entry = {
            "type":       "final_report",
            "generated_at": report["meta"]["generated_at"],
            "overall": {
                "risk_score": report["overall_assessment"]["risk_score"],
                "severity":   report["overall_assessment"]["severity"],
            },
            "ml_analysis":  report.get("ml_analysis", {}),
            "echo_analysis": {
                k: v for k, v in report.get("echo_analysis", {}).items()
                if k != "echo_measurements"  # حذف لیست بلند
            },
            "risk_factors": [
                {"feature": r["feature"], "label": r["label_fa"]}
                for r in report.get("risk_factors", [])
            ],
            "recommendation": report.get("recommendation", {}),
        }

        date_field = f"visits.{visit_date}"
        coll.update_one({"_id": patient_id}, {"$pull": {date_field: {"type": "final_report"}}})
        coll.update_one({"_id": patient_id}, {"$push": {date_field: mongo_entry}})
        client.close()
        print("    گزارش در MongoDB ذخیره شد.")

    except Exception as exc:
        print(f"     خطا در ذخیره MongoDB: {exc}")

def main() -> None:
    patch_sys_argv_from_windows_command_line()
    args = build_parser().parse_args()

    output_root = ensure_dir(Path(args.output_root).expanduser().resolve())
    input_path  = Path(args.video).expanduser().resolve()
    patient_id = input_path.name
    visit_date  = datetime.now().strftime("%Y-%m-%d")

    # ── دریافت اطلاعات بیمار از MongoDB ──────────────────────────────────
    print(f" دریافت اطلاعات بیمار {patient_id}...")
    patient_config = get_patient_config(patient_id)
    print(f" اطلاعات بیمار دریافت شد: {patient_config.get('name', 'بدون نام')}")

    # ── اجرای تحلیل ML (مستقل از ویدیو) ────────────────────────────────
    ml_result = run_ml_analysis(patient_config)

    # ── حالت ML-Only ────────────────────────────────────────────────────
    if args.ml_only:
        if ml_result:
            report = build_final_report(
                patient_config = patient_config,
                ml_result      = ml_result,
                fuzzy_result   = None,
                visit_date     = visit_date,
            )
            report_dir = ensure_dir(
                output_root / safe_name(str(patient_id)) / visit_date / "ml_only_report"
            )
            saved = save_report(report, report_dir, str(patient_id), visit_date)
            print(f"\n گزارش ML-Only ذخیره شد: {saved.get('json')}")
            print("\n" + report.get("patient_report", ""))
        return

    # ── پردازش ویدیو ─────────────────────────────────────────────────────
    all_rows: list[dict] = []

    if input_path.is_dir():
        print(f"\n پردازش پوشه: {input_path}")
        video_extensions = {".avi", ".mp4", ".mov", ".mkv", ".wmv"}
        video_files = [f for f in input_path.iterdir()
                       if f.suffix.lower() in video_extensions]

        if not video_files:
            print(f" فایل ویدیو در {input_path} یافت نشد")
            return

        for video_path in video_files:
            print(f"\n پردازش: {video_path.name}")
            try:
                rows = process_video(
                    video_path, measurement_module, args, output_root,
                    patient_config=patient_config
                )
                all_rows.extend(rows)
            except Exception as exc:
                print(f" خطا در {video_path.name}: {exc}")
                all_rows.append({
                    "video_name": video_path.name,
                    "video_path": str(video_path),
                    "patient_id": patient_id,
                    "error":      str(exc),
                })

        # ذخیره خلاصه ویدیوها
        summary_csv = (
            output_root / str(patient_id) / visit_date / "pipeline_summary.csv"
        )
        os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
        pd.DataFrame(all_rows).to_csv(summary_csv, index=False)
        print(f"\n خلاصه pipeline: {summary_csv}")

        # ── تحلیل فازی اکو ────────────────────────────────────────────
        print(f"\n ارزیابی فازی اکوکاردیوگرافی...")
        fuzzy_result = aggregate_and_evaluate_fuzzy(
            output_root,
            str(patient_id),
            visit_date,
            patient_config,
            rows=all_rows,
            summary_csv_path=summary_csv,
        )
        if fuzzy_result:
            fuzz_cat = fuzzy_result.get("category", "?")
            fuzz_score = fuzzy_result.get("score", 0)
            print(f" نتیجه فازی: {fuzz_cat} (امتیاز: {fuzz_score:.1f})")
        else:
            print("  نتیجه فازی موجود نیست.")

        # ── گزارش نهایی ترکیبی ────────────────────────────────────────
        generate_and_save_final_report(
            output_root    = output_root,
            patient_id     = str(patient_id),
            visit_date     = visit_date,
            patient_config = patient_config,
            ml_result      = ml_result,
            fuzzy_result   = fuzzy_result,
            all_rows       = all_rows,
        )

    else:
        # ── پردازش یک ویدیو ───────────────────────────────────────────
        video_path = resolve_video_path(args.video, cwd=BASE_DIR)
        print(f"\n پردازش ویدیو: {video_path}")
        try:
            all_rows = process_video(
                video_path, measurement_module, args, output_root,
                patient_config=patient_config
            )
        except Exception as exc:
            print(f" خطا: {exc}")
            all_rows = [{
                "video_name": video_path.name,
                "video_path": str(video_path),
                "patient_id": patient_id,
                "error":      str(exc),
            }]

        # برای یک ویدیو هم گزارش ML تولید می‌شود (بدون fuzzy)
        if ml_result:
            report = build_final_report(
                patient_config = patient_config,
                ml_result      = ml_result,
                fuzzy_result   = None,
                echo_rows      = all_rows,
                visit_date     = visit_date,
            )
            report_dir = ensure_dir(
                output_root / safe_name(str(patient_id)) / visit_date / "single_video_report"
            )
            saved = save_report(report, report_dir, str(patient_id), visit_date)
            print(f"\n گزارش ML ذخیره شد: {saved.get('json')}")


if __name__ == "__main__":
    main()
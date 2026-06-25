from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from pipeline.config import CLASSIFIER_MODEL, RESULT_DIR, VIEW_PIPELINES
from pipeline.paths import patch_sys_argv_from_windows_command_line
from pipeline.processing import process_video
from pipeline.results import aggregate_and_evaluate_fuzzy, ensure_dir, generate_final_patient_report, safe_name
import os
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ai_service.mongo_reader import get_patient_config
from ai_service.ml_predictor import MLRiskPredictor
from ai_service.report_generator import build_final_report, save_report

# ── ML Predictor ( اولین باری که کسی بهش نیاز داشت، بساز , یک‌بار لود می‌شه و برای همه بیماران استفاده می‌شه) ─────────
_ml_predictor: MLRiskPredictor | None = None


def get_ml_predictor() -> MLRiskPredictor:
    """Lazy singleton — مدل‌ها فقط یک‌بار از دیسک بارگذاری می‌شوند"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLRiskPredictor()
    return _ml_predictor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Echo pipeline")
    parser.add_argument("video", nargs="?", default=None, help="Input video folder path.")
    parser.add_argument("--patient-id", default=None, help="شناسه بیمار (برای --ml-only)")
    parser.add_argument("--output-root", default=str(RESULT_DIR), help="Root folder for outputs.")
    parser.add_argument("--view", choices=sorted(VIEW_PIPELINES.keys()), default=None,
                        help="Force the view and skip classifier.")
    parser.add_argument("--classifier-model",
                        default=str(CLASSIFIER_MODEL) if CLASSIFIER_MODEL.exists() else None,
                        help="Path to view classifier model.")
    parser.add_argument("--classifier-samples", type=int, default=8,
                        help="Number of sampled frames for classification.")
    parser.add_argument("--device", default=None, help="Torch device for measurement models.")
    parser.add_argument("--default-pixels-per-cm", type=float, default=12.0,
                        help="Fallback scale when automatic ruler detection fails.")
    parser.add_argument("--ml-only", action="store_true",
                        help="فقط ML prediction اجرا شود، بدون پردازش ویدیو.")
    return parser


def run_ml_analysis(patient_config: dict) -> dict | None:
    """
    خروجی نمونه:
    {
        "hd_result": {
            "probability": 0.7279,        # احتمال بیماری قلبی (0-1)
            "confidence":  1.0,           # کیفیت داده (1.0 = همه فیچرها موجود)
            "missing":     [],            # فیچرهای غایب که از median جایگزین شدند
        },
        "cv_result": {
            "probability": 0.0924,
            "confidence":  1.0,
            "missing":     [],
        },
        "combined_score":    41.0,        # میانگین وزنی × 100
        "combined_prob":     0.4102,
        "overall_severity":  "LOW",       # LOW / MODERATE / HIGH / CRITICAL
        "overall_confidence": 1.0,
        "risk_factors": [
            {"feature": "cp", "value": 0, "label_fa": "درد قفسه سینه آنژینی", "label_en": "..."},
            {"feature": "ca", "value": 2, "label_fa": "کاهش جریان کرونری (CA≥1)", "label_en": "..."},
        ]
    }
    """
    try:
        predictor   = get_ml_predictor()
        ml_result   = predictor.predict(patient_config)

        if "error" in ml_result.get("hd_result", {}) or "error" in ml_result.get("cv_result", {}):
            print("     خطا در بارگذاری مدل‌ها:")
            if "error" in ml_result.get("hd_result", {}):
                print(f"      - HD: {ml_result['hd_result']['error']}")
            if "error" in ml_result.get("cv_result", {}):
                print(f"      - CV: {ml_result['cv_result']['error']}")
            return None

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
    build_final_report خروجی نمونه:
    {
        "meta":   {"generated_at": "2026-06-24T21:49:03", "visit_date": "2026-06-24", ...},
        "patient": {"id": "2", "age": 24, "gender": "مرد", "bmi": 22.1, ...},
        "overall_assessment": {"risk_score": 41.0, "severity": "LOW", "severity_color": "#27ae60"},
        "ml_analysis":   { ... همان خروجی run_ml_analysis + probability_pct ... },
        "echo_analysis": {"available": false}  # یا اگر pipeline کامل بود: {"ef": 60, ...}
        "risk_factors":  [{"feature": "ca", "label_fa": "...", "label_en": "..."}],
        "recommendation": {"urgency": "روتین", "doctor": "...", "patient": "...", "lifestyle": "..."},
        "doctor_report":  "متن بلند برای پزشک...",
        "patient_report": "متن ساده برای بیمار...",
    }

    save_report فایل‌های زیر را در report_dir می‌سازد:
        final_report.json      ← گزارش کامل
        doctor_report.txt      ← متن پزشک
        patient_report.txt     ← متن بیمار
        ml_result.json         ← خلاصه ML

    generate_final_patient_report خروجی نمونه:
    {
        "files": {
            "llm_txt":  "result/2/2026-06-24/final_report/llm_patient_report.txt",
            "llm_html": "result/2/2026-06-24/final_report/patient_report.html",
        },
        "mongodb": {"status": "saved", "visit_date": "2026-06-24"}
    }
    """

    report = build_final_report(
        patient_config = patient_config,
        ml_result      = ml_result,
        fuzzy_result   = fuzzy_result,
        echo_rows      = all_rows,
        visit_date     = visit_date,
    )

    report_dir = ensure_dir(output_root / safe_name(patient_id) / visit_date / "final_report")
    save_report(report, report_dir, patient_id, visit_date)
    _save_report_to_mongo(patient_id, visit_date, report)

    try:
        generate_final_patient_report(
            output_root=output_root,
            patient_id=patient_id,
            visit_date=visit_date,
            final_report_json_path=report_dir / "final_report.json",
        )

    except Exception as exc:
        print(f"    خطا در تولید گزارش LLM: {exc}")
        import traceback
        traceback.print_exc()


def _save_report_to_mongo(patient_id: str, visit_date: str, report: dict) -> None:
    mongo_uri = os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/")
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri)
        try:
            db   = client[os.getenv("ECHO_MONGO_DB", "echo_pipeline")]
            coll = db[os.getenv("ECHO_MONGO_COLLECTION", "patients")]

            mongo_entry = {
                "type":         "final_report",
                "generated_at": report["meta"]["generated_at"],
                "overall": {
                    "risk_score": report["overall_assessment"]["risk_score"],
                    "severity":   report["overall_assessment"]["severity"],
                },
                "ml_analysis":  report.get("ml_analysis", {}),
                "echo_analysis": {
                    k: v for k, v in report.get("echo_analysis", {}).items()
                    if k != "echo_measurements"
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
        finally:
            client.close()
    except Exception as exc:
        print(f"     خطا در ذخیره MongoDB: {exc}")


def main() -> None:
    patch_sys_argv_from_windows_command_line()
    args = build_parser().parse_args()

    output_root = ensure_dir(Path(args.output_root).expanduser().resolve())
    visit_date  = datetime.now().strftime("%Y-%m-%d")

    if args.ml_only:
        if not args.patient_id:
            print(" خطا: برای --ml-only باید --patient-id مشخص شود")
            return
        patient_id = args.patient_id
        input_path = None
    else:
        if not args.video:
            print(" خطا: مسیر پوشه ویدیو الزامی است")
            return
        input_path = Path(args.video).expanduser().resolve()
        patient_id = input_path.name

    # get_patient_config :
    # {"user_id": 2, "name": "علی", "age": 24, "sex": 1, "gender": 2, ...}
    patient_config = get_patient_config(patient_id)
    print(f"patient data recive from mongo:  {patient_config.get('name', 'بدون نام')}")

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
                output_root / safe_name(patient_id) / visit_date / "ml_only_report"
            )
            save_report(report, report_dir, patient_id, visit_date)
        return

    # ── پردازش ویدیوها از پوشه بیمار ────────────────────────────────────
    if not input_path.is_dir():
        print(f" خطا: مسیر باید یک پوشه باشد: {input_path}")
        return

    video_extensions = {".avi", ".mp4", ".mov", ".mkv", ".wmv"}
    video_files = [f for f in input_path.iterdir() if f.suffix.lower() in video_extensions]

    if not video_files:
        print(f" فایل ویدیو در {input_path} یافت نشد")
        return

    all_rows: list[dict] = []
    for video_path in video_files:
        print(f"\n پردازش: {video_path.name}")
        try:
            # process_video خروجی  (list of dict، یکی برای هر نما):
            # [{"video_name": "echo.avi", "view": "PLAX", "patient_id": "2",
            #   "ivs_thickness": 0.84, "lv_diameter": None, "aortic_root": None,
            #   "public_event_image": "public/2/2026-06-24/PLAX/event.jpg", ...}]
            rows = process_video(
                video_path, output_root,
                manual_view=args.view,
                classifier_model=args.classifier_model,
                classifier_samples=args.classifier_samples,
                device=args.device,
                default_pixels_per_cm=args.default_pixels_per_cm,
                patient_config=patient_config,
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

    summary_csv = output_root / patient_id / visit_date / "pipeline_summary.csv"
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_rows).to_csv(summary_csv, index=False)

    # aggregate_and_evaluate_fuzzy خروجی :
    # {"score": 15.0, "category": "Normal", "reasons": [],
    #  "text": "Score: 15.0/100 | Category: Normal\nReasons:\n  - All normal.",
    #  "llm_prompt": "بیمار ۲۴ ساله مرد  ...   IVS=0.84cm ..."}
    # یا None اگر هیچ ویدیویی موفق پردازش نشده باشد
    fuzzy_result = aggregate_and_evaluate_fuzzy(
        output_root,
        patient_id,
        visit_date,
        patient_config,
        rows=all_rows,
        summary_csv_path=summary_csv,
    )

    generate_and_save_final_report(
        output_root    = output_root,
        patient_id     = patient_id,
        visit_date     = visit_date,
        patient_config = patient_config,
        ml_result      = ml_result,
        fuzzy_result   = fuzzy_result,
        all_rows       = all_rows,
    )


if __name__ == "__main__":
    main()

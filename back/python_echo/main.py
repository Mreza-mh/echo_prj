from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path


# کنسول ویندوز پیش‌فرض روی cp1252 هست و متن‌های فارسی رو نمی‌تونه چاپ کنه (UnicodeEncodeError)
# پس stdout/stderr رو دستی روی utf-8 ری‌کانفیگ می‌کنیم
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# سایلنت‌کردن لاگ‌های سطح C++ تنسورفلو/absl (oneDNN، GPU و ...)
# باید قبل از import شدن tensorflow (که داخل ai_service.ml_predictor اتفاق می‌افته) تنظیم بشه
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("tensorflow").setLevel(logging.ERROR)

warnings.filterwarnings("ignore", message=".*InconsistentVersionWarning.*")
warnings.filterwarnings("ignore", message="Trying to unpickle estimator.*")
warnings.filterwarnings("ignore", message="X does not have valid feature names.*")

import pandas as pd

from pipeline.config import RESULT_DIR
from pipeline.processing import process_video
from pipeline.results import (
    aggregate_and_evaluate_fuzzy,
    ensure_dir,
    generate_and_save_final_report,
    safe_name,
)

# پوشه‌ی جاری (back/python_echo) رو به sys.path اضافه می‌کنیم تا پکیج ai_service پیدا بشه
sys.path.insert(0, str(Path(__file__).parent))
from ai_service.mongo_reader import get_patient_config
from ai_service.ml_predictor import MLRiskPredictor
from ai_service.report_generator import build_final_report, save_report

_ml_predictor: MLRiskPredictor | None = None


def get_ml_predictor() -> MLRiskPredictor:

    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLRiskPredictor()
    return _ml_predictor



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Echo pipeline")
    parser.add_argument("video",        nargs="?",           default=None, help="Input video folder path.")
    parser.add_argument("--patient-id",                      default=None, help="شناسه بیمار (برای --ml-only)")
    parser.add_argument("--ml-only",    action="store_true",               help="فقط ML prediction، بدون پردازش ویدیو.")
    return parser



def run_ml_analysis(patient_config: dict) -> dict | None:
    """
    ورودی:  patient_config dict (age, sex, height, weight, ap_hi/lo, ...)
    خروجی:  دیکشنری {hd_result, cv_result, combined_score, severity, risk_factors, ...}
            یا None اگر خطا داشت (خطای مدل یا exception)
    """
    try:
        ml_result = get_ml_predictor().predict(patient_config)

        # --- مرحله ۲: چک می‌کنه که هیچ‌کدوم از دو مدل (HD/CV) خطا نداده باشن ---
        hd_err = ml_result.get("hd_result", {}).get("error")
        cv_err = ml_result.get("cv_result", {}).get("error")
        if hd_err or cv_err:
            if hd_err: print(f"      - HD: {hd_err}")
            if cv_err: print(f"      - CV: {cv_err}")
            return None

        return ml_result

    except Exception as exc:
        import traceback
        print(f"    خطا در ML analysis: {exc}")
        traceback.print_exc()
        return None


# ==============================================================================

def main() -> None:
    args = build_parser().parse_args()

    output_root = ensure_dir(RESULT_DIR)                      
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


    patient_config = get_patient_config(patient_id)
    print(f"patient data recive from mongo:  {patient_config.get('name', 'بدون نام')}")


    ml_result = run_ml_analysis(patient_config)

    if args.ml_only:
        if ml_result:
            report = build_final_report(
                patient_config=patient_config, ml_result=ml_result,
                fuzzy_result=None, visit_date=visit_date,
            )
            save_report(report, ensure_dir(output_root / safe_name(patient_id) / visit_date / "ml_only_report"), patient_id, visit_date)
        return


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
            rows = process_video(video_path, output_root, patient_config=patient_config)
            all_rows.extend(rows)
        except Exception as exc:
            print(f" خطا در {video_path.name}: {exc}")
            all_rows.append({"video_name": video_path.name, "video_path": str(video_path),
                                "patient_id": patient_id, "error": str(exc)})

    fuzzy_result = aggregate_and_evaluate_fuzzy(
        output_root, patient_id, visit_date, patient_config,
        rows=all_rows,
    )

    generate_and_save_final_report(
        output_root=output_root, patient_id=patient_id, visit_date=visit_date,
        patient_config=patient_config, ml_result=ml_result,
        fuzzy_result=fuzzy_result, all_rows=all_rows,
    )


if __name__ == "__main__":
    main()

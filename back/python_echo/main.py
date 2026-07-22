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

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
# باید قبل از import شدن tensorflow (که داخل ai_service.ml_predictor اتفاق می‌افته) تنظیم بشه
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
)

# پوشه‌ی جاری (back/python_echo) رو به sys.path اضافه می‌کنیم تا پکیج ai_service پیدا بشه
sys.path.insert(0, str(Path(__file__).parent))
from ai_service.mongo_reader import get_patient_config
from ai_service.ml_predictor import MLRiskPredictor

_ml_predictor: MLRiskPredictor | None = None


def get_ml_predictor() -> MLRiskPredictor:

    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLRiskPredictor()
    return _ml_predictor



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Echo pipeline")
    parser.add_argument("video", help="Input video folder path.")
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


    input_path = Path(args.video).expanduser().resolve()
    patient_id = input_path.name


    patient_config = get_patient_config(patient_id)
    print(f"patient data recive from mongo:  {patient_config.get('name', 'بدون نام')}")


    ml_result = run_ml_analysis(patient_config)
    # print("ml_result : " , ml_result)
    # {
    # "ml_result": {
    #     "hd_result": {
    #     "model": "HD_LogisticRegression",
    #     "probability": 0.2183,
    #     "probability_pct": 21.8,
    #     "confidence": 1.0,
    #     "missing_features": [],
    #     "n_features_used": 18
    #     },
    #     "cv_result": {
    #     "model": "CV_CatBoost",
    #     "probability": 0.0835,
    #     "probability_pct": 8.3,
    #     "confidence": 1.0,
    #     "missing_features": [],
    #     "n_features_used": 20
    #     },
    #     "combined_score": 15.1,
    #     "combined_prob": 0.1509,
    #     "severity": "LOW",
    #     "confidence": 1.0,
    #     "bmi": 22.1,
    #     "risk_factors": [
    #     {
    #         "feature": "cp",
    #         "value": 0,
    #         "label_fa": "درد قفسه سینه آنژینی",
    #         "label_en": "Anginal chest pain"
    #     },
    #     {
    #         "feature": "ca",
    #         "value": 2,
    #         "label_fa": "کاهش جریان کرونری (CA≥1)",
    #         "label_en": "Coronary artery narrowing ≥1"
    #     }
    #     ]
    # }
    # }
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

    # print("all_rows : " , all_rows)        
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



# python main.py echo_input/2






# [
#   {
#     "video_name": "dd.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\dd.avi",
#     "session_dir": "2\\2026-07-13\\a4c_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "a4c_3",
#     "detected_view": "a4c",
#     "classification_source": "in_process",
#     "view_confidence": 0.9859181642532349,

#     "event_name": "End Diastol",
#     "event_frame_number": 60,
#     "frame_image": "2\\2026-07-13\\a4c_3\\internal\\events\\End_Diastol\\frame_0060.jpg",
#     "public_event_image": "2/2026-07-13/a4c_3/media/events/End_Diastol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\dd.avi",
#     "measurement_name": "rv_base",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\a4c_3\\internal\\measurements\\End_Diastol\\rv_base\\rv_base.jpg",
#     "annotated_preview": "2\\2026-07-13\\a4c_3\\internal\\measurements\\End_Diastol\\rv_base\\rv_base.jpg",
#     "public_preview_image": "2/2026-07-13/a4c_3/media/measurements/End_Diastol_rv_base.jpg",
#     "pred_x1": 158,
#     "pred_y1": 266,
#     "pred_x2": 299,
#     "pred_y2": 268,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\rv_base_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 4.714957972982647,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 141.01 px  (158,266)-(299,268)  |  4.715 cm",
#     "pixel_length": 141.01418368376991,
#     "length_cm": 4.714957972982647,
#     "pixels_per_cm": 28.6,
#     "a4c_left_atrium_area_cm2": 24.22490097315272,
#     "a4c_right_atrium_area_cm2": 12.093500904689716,
#     "lv_area_cm2": 34.63983568878674
#   },
#   {
#     "video_name": "dd.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\dd.avi",
#     "session_dir": "2\\2026-07-13\\a4c_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "a4c_3",
#     "detected_view": "a4c",
#     "classification_source": "in_process",
#     "view_confidence": 0.9859181642532349,
#     "event_name": "End Sistol",
#     "event_frame_number": 87,
#     "frame_image": "2\\2026-07-13\\a4c_3\\internal\\events\\End_Sistol\\frame_0087.jpg",
#     "public_event_image": "2/2026-07-13/a4c_3/media/events/End_Sistol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\dd.avi",
#     "measurement_name": "la",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\a4c_3\\internal\\measurements\\End_Sistol\\la\\la.jpg",
#     "annotated_preview": "2\\2026-07-13\\a4c_3\\internal\\measurements\\End_Sistol\\la\\la.jpg",
#     "public_preview_image": "2/2026-07-13/a4c_3/media/measurements/End_Sistol_la.jpg",
#     "pred_x1": 365,
#     "pred_y1": 288,
#     "pred_x2": 371,
#     "pred_y2": 407,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\la_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 4.399462612516291,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 119.15 px  (365,288)-(371,407)  |  4.399 cm",
#     "pixel_length": 119.15116449284078,
#     "length_cm": 4.399462612516291,
#     "pixels_per_cm": 28.6,
#     "a4c_left_atrium_area_cm2": 24.22490097315272,
#     "a4c_right_atrium_area_cm2": 12.093500904689716,
#     "lv_area_cm2": 34.63983568878674
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "End Diastol",
#     "event_frame_number": 32,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\End_Diastol\\frame_0032.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/End_Diastol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "ivs",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Diastol\\ivs\\ivs.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Diastol\\ivs\\ivs.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/End_Diastol_ivs.jpg",
#     "pred_x1": 299,
#     "pred_y1": 179,
#     "pred_x2": 286,
#     "pred_y2": 202,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\ivs_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 0.8371042930537949,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 26.42 px  (299,179)-(286,202)  |  0.837 cm",
#     "pixel_length": 26.419689627245813,
#     "length_cm": 0.8371042930537949,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "End Diastol",
#     "event_frame_number": 32,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\End_Diastol\\frame_0032.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/End_Diastol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "lvid",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Diastol\\lvid\\lvid.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Diastol\\lvid\\lvid.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/End_Diastol_lvid.jpg",
#     "pred_x1": 292,
#     "pred_y1": 205,
#     "pred_x2": 222,
#     "pred_y2": 320,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\lvid_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 4.254335399449017,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 134.63 px  (292,205)-(222,320)  |  4.254 cm",
#     "pixel_length": 134.6291201783626,
#     "length_cm": 4.254335399449017,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "End Diastol",
#     "event_frame_number": 32,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\End_Diastol\\frame_0032.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/End_Diastol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "lvpw",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Diastol\\lvpw\\lvpw.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Diastol\\lvpw\\lvpw.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/End_Diastol_lvpw.jpg",
#     "pred_x1": 218,
#     "pred_y1": 317,
#     "pred_x2": 209,
#     "pred_y2": 348,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\lvpw_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 1.0385239683077299,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 32.28 px  (218,317)-(209,348)  |  1.039 cm",
#     "pixel_length": 32.28002478313795,
#     "length_cm": 1.0385239683077299,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "End Sistol",
#     "event_frame_number": 58,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\End_Sistol\\frame_0058.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/End_Sistol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "lvid",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Sistol\\lvid\\lvid.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Sistol\\lvid\\lvid.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/End_Sistol_lvid.jpg",
#     "pred_x1": 257,
#     "pred_y1": 199,
#     "pred_x2": 206,
#     "pred_y2": 288,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\lvid_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 3.2485757490403975,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 102.58 px  (257,199)-(206,288)  |  3.249 cm",
#     "pixel_length": 102.57680049601859,
#     "length_cm": 3.2485757490403975,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "End Sistol",
#     "event_frame_number": 58,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\End_Sistol\\frame_0058.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/End_Sistol.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "la",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Sistol\\la\\la.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\End_Sistol\\la\\la.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/End_Sistol_la.jpg",
#     "pred_x1": 359,
#     "pred_y1": 271,
#     "pred_x2": 368,
#     "pred_y2": 379,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\la_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 3.5091774051058167,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 108.37 px  (359,271)-(368,379)  |  3.509 cm",
#     "pixel_length": 108.37435120913067,
#     "length_cm": 3.5091774051058167,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "LVOT",
#     "event_frame_number": 45,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\LVOT\\frame_0045.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/LVOT.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "aorta",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\LVOT\\aorta\\aorta.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\LVOT\\aorta\\aorta.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/LVOT_aorta.jpg",
#     "pred_x1": 430,
#     "pred_y1": 182,
#     "pred_x2": 459,
#     "pred_y2": 270,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\aorta_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 2.9754165967600246,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 92.66 px  (430,182)-(459,270)  |  2.975 cm",
#     "pixel_length": 92.65527507918802,
#     "length_cm": 2.9754165967600246,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   },
#   {
#     "video_name": "ssss.avi",
#     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "session_dir": "2\\2026-07-13\\plax_3",
#     "date_folder": "2026-07-13",
#     "view_instance": "plax_3",
#     "detected_view": "plax",
#     "classification_source": "in_process",
#     "view_confidence": 0.9315013885498047,
#     "event_name": "LVOT",
#     "event_frame_number": 45,
#     "frame_image": "2\\2026-07-13\\plax_3\\internal\\events\\LVOT\\frame_0045.jpg",
#     "public_event_image": "2/2026-07-13/plax_3/media/events/LVOT.jpg",
#     "one_frame_video": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\echo_input\\2\\ssss.avi",
#     "measurement_name": "aortic_root",
#     "measurement_status": "ok",
#     "measurement_message": "Weights loaded successfully.",
#     "annotated_video": "2\\2026-07-13\\plax_3\\internal\\measurements\\LVOT\\aortic_root\\aortic_root.jpg",
#     "annotated_preview": "2\\2026-07-13\\plax_3\\internal\\measurements\\LVOT\\aortic_root\\aortic_root.jpg",
#     "public_preview_image": "2/2026-07-13/plax_3/media/measurements/LVOT_aortic_root.jpg",
#     "pred_x1": 396,
#     "pred_y1": 195,
#     "pred_x2": 399,
#     "pred_y2": 289,
#     "weights_path": "C:\\Users\\SiBIRAN\\Desktop\\echo_prj\\back\\python_echo\\pipeline\\measurement\\weights\\2D_models\\aortic_root_weights.ckpt",
#     "device": "cpu",
#     "scale_source": "ruler_estimate",
#     "measurement_value": 3.0468998550532214,
#     "measurement_unit": "cm",
#     "measurement_text": "Length: 94.05 px  (396,195)-(399,289)  |  3.047 cm",
#     "pixel_length": 94.04786015641186,
#     "length_cm": 3.0468998550532214,
#     "pixels_per_cm": 32.6,
#     "a4c_left_atrium_area_cm2": null,
#     "a4c_right_atrium_area_cm2": null,
#     "lv_area_cm2": null
#   }
# ]
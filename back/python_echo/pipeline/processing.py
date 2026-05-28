from __future__ import annotations
# """این فایل اجرای کامل پایپ‌لاین را مرحله‌به‌مرحله پیش می‌برد و خروجی داخلی و خروجی قابل‌نمایش را می‌سازد."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import cv2
import pandas as pd

from pipeline.classification import (
    build_public_classification_result,
    normalize_view_label,
    run_classification,
    save_classification_outputs,
)
from pipeline.config import DEFAULT_ONE_FRAME_FPS, DEFAULT_ONE_FRAME_REPEAT, MODEL_VIDEO_SIZE, VIEW_PIPELINES
from pipeline.events import extract_events
from pipeline.measurement.a4c_volume import run_a4c_atrial_areas
from pipeline.measurement.lv_segmentation import run_lv_segmentation
from pipeline.measurement import scale as scale_module
from pipeline.measurement.scale import visualize_scale_result

from pipeline.results import (
    build_session_paths,
    copy_public_file,
    ensure_dir,
    path_for_frontend,
    relative_to_root,
    safe_name,
    save_public_result_to_mongo,
    write_json,
)


def build_measurement_fields(summary: dict[str, Any]) -> dict[str, Any]:
    # """
    # ورودی: summary = {
    #     'frame_number': 0,
    #     'pred_x1': 299, 'pred_y1': 179, 'pred_x2': 286, 'pred_y2': 202,
    #     'pixel_length': 26.419689627245813,
    #     'length_cm': 0.8371042930537949,
    #     'pixels_per_cm': 32.6,
    #     'measurement_value': 0.8371042930537949,
    #     'measurement_unit': 'cm',
    #     'measurement_text': 'Length: 26.42 px  (299,179)-(286,202)  |  0.837 cm'
    # }
    # خروجی: دیکشنری شامل ۶ فیلد استاندارد اندازه‌گیری
    # """
    return {
        "measurement_value": summary.get("measurement_value"),   # 0.8371042930537949
        "measurement_unit": summary.get("measurement_unit"),     # 'cm'
        "measurement_text": summary.get("measurement_text"),     # 'Length: 26.42 px  (299,179)-(286,202)  |  0.837 cm'
        "pixel_length": summary.get("pixel_length"),             # 26.419689627245813
        "length_cm": summary.get("length_cm"),                   # 0.8371042930537949
        "pixels_per_cm": summary.get("pixels_per_cm"),           # 32.6
    }


def build_internal_row_base(
    video_path: Path,                                   # C:\Users\SiBIRAN\Desktop\prj\404445623\ssss.avi
    session_paths: dict[str, Any],                      # دیکشنری مسیرهای جلسه (session_dir, date_dir, view_name, ...)
    classification_result: dict[str, Any],              # خروجی run_classification
    output_root: Path,                                  # C:\Users\SiBIRAN\Desktop\prj\result
) -> dict[str, Any]:
    # """
    # یک دیکشنری پایه برای تمام سطرهای اندازه‌گیری این ویدیو می‌سازد.
    # خروجی شامل: نام ویدیو، مسیر ویدیو، پوشه جلسه، تاریخ، نام نمای یکتا،
    #             نمای تشخیص‌داده‌شده، منبع کلاسیفیکیشن، و اطمینان مدل.
    # """
    return {
        "video_name": video_path.name,                  # 'ssss.avi'
        "video_path": str(video_path),                  # 'C:\\Users\\SiBIRAN\\Desktop\\prj\\404445623\\ssss.avi'
        "session_dir": relative_to_root(                # '404445623\\2026-05-18\\plax_3'
            session_paths["session_dir"], output_root
        ),
        "date_folder": session_paths["date_dir"].name,  # '2026-05-18'
        "view_instance": session_paths["view_name"],    # 'plax_3'
        "detected_view": classification_result.get("prediction"),   # 'plax'
        "classification_source": classification_result.get("source"), # 'in_process'
        "view_confidence": classification_result.get("confidence"),   # 0.9315013363957405
    }


def build_public_measurement_row(row: dict[str, Any]) -> dict[str, Any]:
    # """
    # از یک سطر داخلی (کامل)، یک سطر عمومی (خلاصه برای کاربر نهایی) می‌سازد.
    # فقط فیلدهای ضروری و قابل‌نمایش را نگه می‌دارد.
    # """
    return {
        "event_name": row.get("event_name"),                          # 'End Diastol'
        "event_frame_number": row.get("event_frame_number"),          # 32
        "measurement_name": row.get("measurement_name"),              # 'ivs'
        "status": row.get("measurement_status"),                      # 'ok'
        "message": row.get("measurement_message"),                    # پیام بارگذاری وزن‌ها
        "value": row.get("measurement_value"),                        # 0.8371042930537949
        "unit": row.get("measurement_unit"),                          # 'cm'
        "text": row.get("measurement_text"),                          # 'Length: 26.42 px  ...  |  0.837 cm'
        "length_cm": row.get("length_cm"),                            # 0.8371042930537949
        "pixels_per_cm": row.get("pixels_per_cm"),                    # 32.6
        "event_frame_image": row.get("public_event_image"),           # مسیر نسبی تصویر رویداد در پوشه public
        "measurement_preview_image": row.get("public_preview_image"), # مسیر نسبی تصویر اندازه‌گیری در پوشه public
    }


def save_reports(
    *,
    video_path: Path,                                # مسیر فایل ویدیو
    output_root: Path,                               # پوشه ریشه خروجی
    session_paths: dict[str, Any],                   # مسیرهای جلسه
    patient_id: str | None,                          # '404445623'
    patient_name: str | None,                        # None (مگر با آرگومان داده شود)
    patient_config: dict[str, Any] | None = None,    # {'gender': 'male', 'weight': 10, 'height': 160}
    classification_result: dict[str, Any],           # نتیجه کلاسیفیکیشن
    events_result: dict[str, Any],                   # نتیجه استخراج رویدادها
    internal_rows: list[dict[str, Any]],             # سطرهای داخلی (جزئیات کامل)
    public_rows: list[dict[str, Any]],               # سطرهای عمومی (خلاصه)
    a4c_volume_report: dict[str, Any] | None,        # گزارش حجم دهلیزها (فقط برای a4c)
    lv_volume_report: dict[str, Any] | None = None,  # گزارش حجم بطن چپ (برای a4c/a2c)
) -> None:
    # """
    # تمام خروجی‌های یک ویدیو را ذخیره می‌کند:
    #   - CSV داخلی (measurement_results_full.csv)
    #   - CSV عمومی (measurements.csv)
    #   - JSON نتیجه عمومی (result.json)
    #   - JSON گزارش داخلی (run_report.json)
    #   - ارسال نتیجه به MongoDB
    # """

    # مسیر فایل‌های خروجی
    internal_root = Path(session_paths.get("internal_root", output_root))
    public_root = Path(session_paths.get("public_root", output_root))

    internal_csv_path = Path(session_paths["internal_reports_dir"]) / "measurement_results_full.csv"
    public_csv_path = Path(session_paths["public_reports_dir"]) / "measurements.csv"
    internal_report_path = Path(session_paths["internal_reports_dir"]) / "run_report.json"
    public_result_path = Path(session_paths["public_reports_dir"]) / "result.json"

    # ذخیره CSV ها
    pd.DataFrame(internal_rows).to_csv(internal_csv_path, index=False)
    pd.DataFrame(public_rows).to_csv(public_csv_path, index=False)

    # آماده‌سازی بخش a4c برای خروجی عمومی (در صورت وجود)
    public_a4c = None
    if a4c_volume_report:
        public_a4c = {
            "pixels_per_cm": a4c_volume_report.get("pixels_per_cm"),  # 28.6
            "areas_cm2": a4c_volume_report.get("areas_cm2"),          # {'right_atrium': 11.06..., 'left_atrium': 21.25...}
            "overlay_image": copy_public_file(                        # کپی تصویر overlay به پوشه public
                a4c_volume_report.get("saved_paths", {}).get("overlay_png"),
                Path(session_paths["public_measurements_dir"]) / "a4c_atrial_overlay.png",
                public_root,
            ) if a4c_volume_report.get("saved_paths", {}).get("overlay_png") else None,
        }

    # آماده‌سازی بخش lv برای خروجی عمومی (در صورت وجود)
    public_lv = None
    if lv_volume_report:
        public_lv = {
            "pixels_per_cm": lv_volume_report.get("pixels_per_cm"),  # 28.6
            "area_cm2": lv_volume_report.get("area_cm2"),            # 34.63983568878674
            "overlay_image": copy_public_file(                        # کپی تصویر overlay به پوشه public
                lv_volume_report.get("saved_paths", {}).get("overlay_png"),
                Path(session_paths["public_measurements_dir"]) / "lv_segmentation_overlay.png",
                public_root,
            ) if lv_volume_report.get("saved_paths", {}).get("overlay_png") else None,
        }

    # ساخت دیکشنری نتیجه عمومی (result.json)
    public_result = {
        "patient": {
            "id": patient_id,                    # '404445623'
            "name": patient_name,                # None
            **(patient_config or {})             # {'gender': 'male', 'weight': 10, 'height': 160}
        },
        "study": {
            "video_name": video_path.name,       # 'dd.avi' یا 'ssss.avi'
            "processed_at": datetime.now().isoformat(timespec="seconds"),  # '2026-05-18T...'
            "detected_view": classification_result.get("prediction"),      # 'a4c' یا 'plax'
            "session_dir": path_for_frontend(session_paths["public_session_dir"]),
            "view_instance": session_paths["view_name"],   # 'a4c_3' یا 'plax_3'
        },
        "classification": build_public_classification_result(classification_result),
        "measurements": public_rows,             # لیست اندازه‌گیری‌های عمومی
        "a4c_volume": public_a4c,                # None یا اطلاعات حجم دهلیز
        "lv_volume": public_lv,                  # None یا اطلاعات حجم بطن
        "files": {
            "classification_json": path_for_frontend(
                Path(session_paths["public_reports_dir"]) / "classification.json"
            ),
            "classification_csv": path_for_frontend(
                Path(session_paths["public_reports_dir"]) / "classification.csv"
            ),
            "measurements_csv": path_for_frontend(public_csv_path),
            "result_json": path_for_frontend(public_result_path),
        },
    }
    write_json(public_result, public_result_path)      # ذخیره result.json

    # ارسال به MongoDB (اگر در دسترس باشد)
    mongo_result = save_public_result_to_mongo(public_result)
    # mongo_result: {"status": "stored", ...} یا {"status": "skipped", ...}

    # ساخت دیکشنری گزارش داخلی (run_report.json)
    internal_report = {
        "video_name": video_path.name,
        "video_path": str(video_path),
        "patient": {
            "id": patient_id,
            "name": patient_name,
            **(patient_config or {})
        },
        "classification": classification_result,
        "events": {
            "event_frames": events_result.get("event_frames", {}),
            # {'End Diastol': 60, 'End Sistol': 87}
            "events_csv": relative_to_root(events_result.get("events_csv"), internal_root),
        },
        "measurements_csv": relative_to_root(internal_csv_path, internal_root),
        "measurements": internal_rows,
        "a4c_volume": a4c_volume_report,
        "lv_volume": lv_volume_report,
        "mongo_store": mongo_result,
        "public_result_json": path_for_frontend(public_result_path),
    }
    write_json(internal_report, internal_report_path)  # ذخیره run_report.json


def process_video(
    video_path: Path,                       # C:\Users\SiBIRAN\Desktop\prj\404445623\dd.avi
    measurement_module: object,             # ماژول inference_2d (مدل‌های DeepLabV3+)
    args,                                   # آرگومان‌های خط فرمان (Namespace)
    output_root: Path,                      # C:\Users\SiBIRAN\Desktop\prj\result
    patient_config: dict[str, Any] | None = None,  # {'gender': 'male', 'weight': 10, 'height': 160}
    ) -> list[dict[str, Any]]:
    # """
    # تابع اصلی پردازش یک ویدیوی اکوکاردیوگرافی.

    # مراحل:
    #   ۱) کلاسیفیکیشن (تشخیص نمای اکو: a4c/plax/...)
    #   ۲) ساخت پوشه‌های جلسه
    #   ۳) تعیین شناسه بیمار
    #   ۴) بررسی پشتیبانی از نما
    #   ۵) استخراج رویدادهای ECG و ذخیره فریم‌ها
    #   ۶) تخمین مقیاس (pixels per cm) از خط‌کش
    #   ۷) اجرای مدل‌های اندازه‌گیری روی هر رویداد
    #   ۸) محاسبه حجم دهلیز و بطن (مخصوص a4c/a2c)
    #   ۹) ذخیره تمام گزارش‌ها

    # خروجی: لیستی از دیکشنری‌ها (هر دیکشنری = یک سطر اندازه‌گیری)
    # """

    # ================================================================================================
    # ۱. کلاسیفیکیشن (تشخیص خودکار یا دستی نمای اکو)
    # ================================================================================================
    classification_result = run_classification(
        video_path,
        manual_view=args.view,                # None (اگر کاربر --view ندهد)
        classifier_model=args.classifier_model,
        classifier_samples=args.classifier_samples,  # 8
    )
    # classification_result = {
    #     "video_path": "C:\\Users\\SiBIRAN\\Desktop\\prj\\404445623\\dd.avi",
    #     "model_path": "C:\\...\\mymodel_echocv_500-500-8_adam_16_0.9394.h5",
    #     "sample_count": 8,
    #     "sampled_frame_indices": [0, 14, 28, 43, 57, 71, 85, 99],
    #     "total_frames": 102,
    #     "prediction": "a4c",                  # رشته نمای تشخیص‌داده‌شده
    #     "confidence": 0.9859181419014931,      # اطمینان مدل (0 تا 1)
    #     "class_scores": {                      # امتیاز هر کلاس (جمع = 1)
    #         "plax": 0.0012, "psax-av": 0.0008, "psax-mv": 0.0011,
    #         "psax-ap": 0.0009, "a4c": 0.9859, "a5c": 0.0034,
    #         "a3c": 0.0021, "a2c": 0.0046
    #     },
    #     "frame_results": [...],               # نتیجه تک‌تک ۸ فریم
    #     "source": "in_process",               # "in_process" یعنی مدل تصمیم گرفته
    #     "classifier_python": "C:\\Users\\...\\python.exe"
    # }

    # نرمال‌سازی نام نما (حروف کوچک، بدون فاصله اضافی)
    detected_view = normalize_view_label(classification_result["prediction"])
    # detected_view = "a4c"

    patient_id = patient_config.get("id") if patient_config else getattr(args, "patient_id", None)
    if not patient_id:
        patient_id = video_path.parent.name if video_path.parent.name != "." else safe_name(video_path.stem)

    # ================================================================================================
    # ۲. ساخت پوشه‌های جلسه
    # ================================================================================================
    session_paths = build_session_paths(output_root, video_path, detected_view, patient_id=patient_id)
    # session_paths = {
    #     "video_dir": Path("C:/Users/.../result/404445623"),
    #     "date_dir": Path("C:/Users/.../result/404445623/2026-05-18"),
    #     "session_dir": Path("C:/Users/.../result/404445623/2026-05-18/a4c_3"),
    #     "view_name": "a4c_3",                 # اگر قبلاً a4c و a4c_2 وجود داشته باشند
    #     "internal_events_dir": Path(".../a4c_3/internal/events"),
    #     "internal_measurements_dir": Path(".../a4c_3/internal/measurements"),
    #     "internal_reports_dir": Path(".../a4c_3/internal/reports"),
    #     "public_events_dir": Path(".../a4c_3/public/media/events"),
    #     "public_measurements_dir": Path(".../a4c_3/public/media/measurements"),
    #     "public_reports_dir": Path(".../a4c_3/public/reports"),
    # }

    # ذخیره classification.json و classification.csv در پوشه public/reports
    save_classification_outputs(Path(session_paths["public_reports_dir"]), classification_result)

    # ================================================================================================
    # ۳. تعیین شناسه بیمار
    # ================================================================================================
    # patient_config = {'gender': 'male', 'weight': 10, 'height': 160}
    # پس patient_config.get("id") → None (چون کلید "id" در config.json نبود)
    # patient_id = "404445623"

    # ================================================================================================
    # ۴. بررسی پشتیبانی از نمای تشخیص‌داده‌شده
    # ================================================================================================
    if detected_view not in VIEW_PIPELINES:
        # VIEW_PIPELINES = {"plax": {...}, "a4c": {...}}
        # اگر نما پشتیبانی نشود (مثلاً "a5c"):
        unsupported_row = {
            "video_name": video_path.name,
            "video_path": str(video_path),
            "measurement_status": "unsupported_view",
            "measurement_message": f"View '{detected_view}' is not wired in the pipeline yet.",
        }
        save_reports(
            video_path=video_path, output_root=output_root, session_paths=session_paths,
            patient_id=patient_id, patient_name=getattr(args, "patient_name", None),
            patient_config=patient_config, classification_result=classification_result,
            events_result={"event_frames": {}, "events_csv": None},
            internal_rows=[unsupported_row],
            public_rows=[build_public_measurement_row(unsupported_row)],
            a4c_volume_report=None,
        )
        return [unsupported_row]

    # ================================================================================================
    # ۵. استخراج رویدادهای ECG
    # ================================================================================================
    pipeline_config = VIEW_PIPELINES[detected_view]
    #  a4c: pipeline_config = {
    #     "events": ["End Diastol", "End Sistol"],
    #     "event_models": {
    #         "End Diastol": ["rv_base"],
    #         "End Sistol": ["rv_base"],
    #     },
    # }


    required_events = pipeline_config["events"]
    # a4c  → ["End Diastol", "End Sistol"]
    # plax → ["End Diastol", "End Sistol", "LVOT"]

    events_result = extract_events(video_path, session_paths["internal_events_dir"], required_events)
    # events_result = {
    #     "total_frames": 102,
    #     "event_frames": {
    #         "End Diastol": 60,          # فریم شماره ۶۰
    #         "End Sistol": 87,           # فریم شماره ۸۷
    #     },
    #     "saved_frames": {
    #         "End Diastol": "C:\\Users\\...\\a4c_3\\internal\\events\\End_Diastol\\frame_0060.jpg",
    #         "End Sistol": "C:\\Users\\...\\a4c_3\\internal\\events\\End_Sistol\\frame_0087.jpg",
    #     },
    #     "events_csv": "C:\\Users\\...\\a4c_3\\internal\\events\\event_frames.csv",
    # }

    # ================================================================================================
    # ۶. ساخت سطر پایه (row_base) برای همه اندازه‌گیری‌های این ویدیو
    # ================================================================================================
    row_base = build_internal_row_base(video_path, session_paths, classification_result, output_root)
    # row_base = {
    #     "video_name": "dd.avi",
    #     "video_path": "C:\\Users\\...\\404445623\\dd.avi",
    #     "session_dir": "404445623\\2026-05-18\\a4c_3",
    #     "date_folder": "2026-05-18",
    #     "view_instance": "a4c_3",
    #     "detected_view": "a4c",
    #     "classification_source": "in_process",
    #     "view_confidence": 0.9859181419014931,
    # }

    # ================================================================================================
    # ۷. تخمین مقیاس (pixels per cm) از خط‌کش تصویر
    # ================================================================================================
    cap = cv2.VideoCapture(str(video_path))     # باز کردن ویدیو
    ret, original_frame = cap.read()            # ret: True/False
                                                # original_frame: np.ndarray (BGR, shape مثلاً 1080x1920x3)
    cap.release()

    fallback_scale = float(args.default_pixels_per_cm)   # 12.0 (مقدار پیش‌فرض از آرگومان)

    global_pixels_per_cm, global_scale_source = scale_module.estimate_pixels_per_cm_from_bgr(
        original_frame, default_pixels_per_cm=fallback_scale
    )
    # a4c:  global_pixels_per_cm = 28.60,  global_scale_source = "ruler_estimate"
    # plax: global_pixels_per_cm = 32.60,  global_scale_source = "ruler_estimate"

    # ذخیره تصویر دیباگ برای بررسی صحت تشخیص خط‌کش
    scale_module.visualize_scale_result(
        original_frame, global_pixels_per_cm, global_scale_source,
        save_path=str(Path(session_paths["internal_reports_dir"]) / "debug_scale_output.jpg")
    )

    # ================================================================================================
    # ۸. حلقه اصلی: پردازش هر رویداد و اجرای مدل‌های اندازه‌گیری روی فریم مربوطه
    # ================================================================================================
    internal_rows = []       # سطرهای داخلی (جزئیات کامل برای دیباگ و گزارش)
    public_rows = []         # سطرهای عمومی (خلاصه برای کاربر نهایی)
    volume_context = None    # ذخیره فریم اول a4c/a2c برای محاسبات حجم دهلیز و بطن

    for event_name in required_events:
        # event_name = "End Diastol" (اولین دور حلقه)
        frame_number = events_result["event_frames"].get(event_name)   # 60
        frame_path = events_result["saved_frames"].get(event_name)     # "C:\\Users\\...\\frame_0060.jpg"

        # ----- ۸-الف. بررسی وجود فریم -----
        if frame_number is None or not frame_path:
            # اگر فریم این رویداد پیدا نشد → سطر خطا
            row = {**row_base, "event_name": event_name, "measurement_status": "missing_event_frame"}
            internal_rows.append(row)
            continue

        # ----- ۸-ب. کپی فریم رویداد به پوشه عمومی -----
        public_event_image = copy_public_file(
            frame_path,                                                          # مسیر مبدأ
            Path(session_paths["public_events_dir"]) / f"{safe_name(event_name)}.jpg",  # مسیر مقصد: .../public/media/events/End_Diastol.jpg
            output_root
        )
        # public_event_image = "404445623\\2026-05-18\\a4c_3\\public\\media\\events\\End_Diastol.jpg"

        # ----- ۸-پ. خواندن تصویر فریم -----
        frame_bgr = cv2.imread(str(frame_path))
        # frame_bgr: np.ndarray با ابعاد مثلاً (507, 612, 3) — BGR
        if frame_bgr is None:
            continue



        segment_height, segment_width = frame_bgr.shape[:2]
        # segment_height = 507, segment_width = 612

        # استفاده از مقدار محاسبه‌شده‌ی global برای تمام فریم‌ها
        pixels_per_cm = global_pixels_per_cm      # 28.60 (a4c) یا 32.60 (plax)
        scale_source = global_scale_source        # "ruler_estimate"

        # ----- ۸-ت. ذخیره فریم برای محاسبات حجم (فقط a4c/a2c) -----
        if (detected_view == "a4c" or detected_view == "a2c") and volume_context is None:
            volume_context = {
                "bgr": frame_bgr,                # تصویر BGR اولین فریم
                "pixels_per_cm": float(pixels_per_cm)  # 28.6
            }

        # ----- ۸-ث. اجرای مدل‌های اندازه‌گیری مربوط به این رویداد -----
        for measurement_name in pipeline_config["event_models"].get(event_name, []):
            # a4c: ["rv_base"]
            # plax End Diastol: ["ivs"], End Sistol: ["lvid"], LVOT: ["aorta", "aortic_root"]

            measurement_dir = ensure_dir(
                Path(session_paths["internal_measurements_dir"]) / safe_name(event_name) / measurement_name
            )
            # measurement_dir = Path(".../internal/measurements/End_Diastol/rv_base")

            annotated_output_path = measurement_dir / f"{measurement_name}.jpg"
            # annotated_output_path = Path(".../internal/measurements/End_Diastol/rv_base/rv_base.jpg")

            try:
                # ----- ۸-ث-۱. اجرای مدل DeepLabV3+ -----
                measurement_result = measurement_module.run_single_inference(
                    model_weights=measurement_name,   # "rv_base"
                    file_path=str(frame_path),        # "C:\\Users\\...\\frame_0060.jpg"
                    output_path=str(annotated_output_path),
                    device=args.device,               # None → خودکار (cpu چون ویندوز)
                    pixels_per_cm=pixels_per_cm,      # 28.6
                    segment_width=segment_width,      # 612
                    segment_height=segment_height,    # 507
                )
                # measurement_result = {
                #     "measurement_name": "rv_base",
                #     "status": "ok",                    # "ok" یا "partial"
                #     "load_message": "Weights loaded successfully.",
                #     "device": "cpu",
                #     "weights_path": "C:\\Users\\...\\rv_base_weights.ckpt",
                #     "input_path": "C:\\Users\\...\\frame_0060.jpg",
                #     "output_path": "C:\\Users\\...\\rv_base.jpg",
                #     "preview_image": "C:\\Users\\...\\rv_base.jpg",   # همان output_path
                #     "coordinates_csv": "C:\\Users\\...\\rv_base.csv",
                #     "frame_count": 1,
                #     "summary": {
                #         "frame_number": 0,
                #         "pred_x1": 158, "pred_y1": 266,
                #         "pred_x2": 299, "pred_y2": 268,
                #         "pixel_length": 141.01418368376991,
                #         "length_cm": 4.714957972982647,
                #         "pixels_per_cm": 28.6,
                #         "measurement_value": 4.714957972982647,
                #         "measurement_unit": "cm",
                #         "measurement_text": "Length: 141.01 px  (158,266)-(299,268)  |  4.715 cm"
                #     }
                # }

                summary = measurement_result["summary"]
                # summary = {
                #     "frame_number": 0,
                #     "pred_x1": 158, "pred_y1": 266,
                #     "pred_x2": 299, "pred_y2": 268,
                #     "pixel_length": 141.01418368376991,
                #     "length_cm": 4.714957972982647,
                #     "pixels_per_cm": 28.6,
                #     "measurement_value": 4.714957972982647,
                #     "measurement_unit": "cm",
                #     "measurement_text": "Length: 141.01 px  (158,266)-(299,268)  |  4.715 cm"
                # }

                # ----- ۸-ث-۲. کپی تصویر اندازه‌گیری‌شده به پوشه عمومی -----
                public_preview_image = copy_public_file(
                    measurement_result.get("preview_image"),
                    Path(session_paths["public_measurements_dir"]) / f"{safe_name(event_name)}_{measurement_name}.jpg",
                    output_root,
                )
                # public_preview_image = "404445623\\2026-05-18\\a4c_3\\public\\media\\measurements\\End_Diastol_rv_base.jpg"

                # ----- ۸-ث-۳. ساخت سطر داخلی کامل -----
                row = {
                    **row_base,                                     # اطلاعات پایه (ویدیو، نما، جلسه)
                    "event_name": event_name,                       # "End Diastol"
                    "event_frame_number": frame_number,             # 60
                    "frame_image": relative_to_root(frame_path, output_root),
                    "public_event_image": public_event_image,       # مسیر نسبی تصویر رویداد در public
                    "one_frame_video": relative_to_root(video_path, output_root),
                    "measurement_name": measurement_name,           # "rv_base"
                    "measurement_status": measurement_result["status"],  # "ok"
                    "measurement_message": measurement_result["load_message"],  # "Weights loaded successfully."
                    "annotated_video": relative_to_root(measurement_result["output_path"], output_root),
                    "annotated_preview": relative_to_root(measurement_result["preview_image"], output_root),
                    "public_preview_image": public_preview_image,
                    "coordinates_csv": relative_to_root(measurement_result["coordinates_csv"], output_root),
                    "pred_x1": summary["pred_x1"],                  # 158
                    "pred_y1": summary["pred_y1"],                  # 266
                    "pred_x2": summary["pred_x2"],                  # 299
                    "pred_y2": summary["pred_y2"],                  # 268
                    "weights_path": measurement_result["weights_path"],
                    "device": measurement_result["device"],         # "cpu"
                    "scale_source": scale_source,                   # "ruler_estimate"
                    **build_measurement_fields(summary),            # باز کردن فیلدهای اندازه‌گیری
                }

            except Exception as exc:
                # در صورت خطا در اجرای مدل
                row = {
                    **row_base,
                    "event_name": event_name,
                    "event_frame_number": frame_number,
                    "frame_image": relative_to_root(frame_path, output_root),
                    "public_event_image": public_event_image,
                    "one_frame_video": relative_to_root(video_path, output_root),
                    "measurement_name": measurement_name,
                    "measurement_status": "error",
                    "measurement_message": str(exc),
                    "pixels_per_cm": pixels_per_cm,
                    "scale_source": scale_source,
                    "device": args.device,
                }

            internal_rows.append(row)
            public_rows.append(build_public_measurement_row(row))  # خلاصه برای کاربر

    # ================================================================================================
    # ۹. محاسبات حجم (دهلیز و بطن) — فقط برای نماهای a4c و a2c
    # ================================================================================================
    a4c_volume_report = None
    lv_volume_report = None

    if volume_context is not None:
        # ----- ۹-الف. محاسبه سطح دهلیزها (فقط a4c) -----
        if detected_view == "a4c":
            a4c_volume_report = run_a4c_atrial_areas(
                volume_context["bgr"],                       # تصویر BGR
                float(volume_context["pixels_per_cm"]),      # 28.6
                output_dir=str(Path(session_paths["internal_reports_dir"]) / "a4c_volume"),
            )
            # a4c_volume_report = {
            #     "pixels_per_cm": 28.6,
            #     "best_center": {"x": 306, "y": 253},
            #     "areas_px": {"right_atrium": 9054, "left_atrium": 17384},
            #     "areas_cm2": {
            #         "right_atrium": 11.066555821800577,    # مساحت به cm²
            #         "left_atrium": 21.252873001124748
            #     },
            #     "saved_paths": {
            #         "overlay_png": "C:\\Users\\...\\a4c_volume\\a4c_atrial_overlay.png",
            #         "areas_json": "C:\\Users\\...\\a4c_volume\\a4c_area_cm2.json"
            #     }
            # }

        # ----- ۹-ب. محاسبه سطح بطن چپ با U-Net++ (a4c و a2c) -----
        if detected_view in ["a4c", "a2c"]:
            weights_path = Path(__file__).parent / "measurement" / "models" / "best.pth"
            if weights_path.exists():
                lv_volume_report = run_lv_segmentation(
                    volume_context["bgr"],                       # تصویر BGR
                    float(volume_context["pixels_per_cm"]),      # 28.6
                    model_path=str(weights_path),
                    device=args.device,
                    output_dir=str(Path(session_paths["internal_reports_dir"]) / "lv_volume"),
                )
                # lv_volume_report = {
                #     "pixels_per_cm": 28.6,
                #     "area_px": 28340,
                #     "area_cm2": 34.63983568878674,             # مساحت LV به cm²
                #     "saved_paths": {
                #         "overlay_png": "C:\\Users\\...\\lv_volume\\lv_segmentation_overlay.png",
                #         "area_json": "C:\\Users\\...\\lv_volume\\lv_area_cm2.json"
                #     }
                # }

    # Attach per-video derived metrics to each row so downstream fuzzy aggregation
    # can run from pipeline_summary rows without re-reading session folders.
    la_area_cm2 = None
    ra_area_cm2 = None
    if a4c_volume_report:
        areas_cm2 = a4c_volume_report.get("areas_cm2", {})
        la_area_cm2 = areas_cm2.get("left_atrium")
        ra_area_cm2 = areas_cm2.get("right_atrium")
    lv_area_cm2 = lv_volume_report.get("area_cm2") if lv_volume_report else None
    for row in internal_rows:
        row["a4c_left_atrium_area_cm2"] = la_area_cm2
        row["a4c_right_atrium_area_cm2"] = ra_area_cm2
        row["lv_area_cm2"] = lv_area_cm2

    # ================================================================================================
    # ۱۰. ذخیره تمام گزارش‌ها
    # ================================================================================================
    save_reports(
        video_path=video_path,                           # مسیر ویدیو
        output_root=output_root,                         # پوشه ریشه خروجی
        session_paths=session_paths,                     # مسیرهای جلسه
        patient_id=patient_id,                           # "404445623"
        patient_name=getattr(args, "patient_name", None), # None
        patient_config=patient_config,                   # {'gender': 'male', 'weight': 10, 'height': 160}
        classification_result=classification_result,     # نتیجه کلاسیفیکیشن
        events_result=events_result,                     # نتیجه رویدادها
        internal_rows=internal_rows,                     # ۲ سطر برای a4c، ۴ سطر برای plax
        public_rows=public_rows,                         # نسخه خلاصه‌شده
        a4c_volume_report=a4c_volume_report,             # None یا اطلاعات حجم دهلیز
        lv_volume_report=lv_volume_report,               # None یا اطلاعات حجم بطن
    )

    # ================================================================================================
    # ۱۱. بازگشت نتیجه
    # ================================================================================================
    return internal_rows
    # خروجی: لیستی از دیکشنری‌ها
    # برای a4c:  [{"event_name": "End Diastol", "measurement_name": "rv_base", ...},
    #             {"event_name": "End Sistol", "measurement_name": "rv_base", ...}]
    # برای plax: [{"event_name": "End Diastol", "measurement_name": "ivs", ...},
    #             {"event_name": "End Sistol", "measurement_name": "lvid", ...},
    #             {"event_name": "LVOT", "measurement_name": "aorta", ...},
    #             {"event_name": "LVOT", "measurement_name": "aortic_root", ...}]

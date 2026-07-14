from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from pipeline.classification import run_classification
from pipeline.config import DEFAULT_PIXELS_PER_CM, VIEW_PIPELINES
from pipeline.events import extract_events
from pipeline.measurement.a4c_volume import run_a4c_atrial_areas
from pipeline.measurement.inference_2d import run_single_inference
from pipeline.measurement.lv_segmentation import run_lv_segmentation
from pipeline.measurement import scale as scale_module

from pipeline.results import (
    copy_public_file,
    ensure_dir,
    relative_to_root,
    safe_name,
    save_reports,
    setup_video_session,
)

# ==============================================================================
# هر «row» یک اندازه‌گیری از یک ویدیو است و دو نسخه دارد:
#   internal_row : همه‌ی فیلدها (مسیرهای داخلی، پیکسل، دیباگ) — در run_report.json ذخیره می‌شود
#   public_row   : زیرمجموعه‌ی امن برای فرانت — در result.json و MongoDB ذخیره می‌شود
# ساختِ internal_row = row_base (مشترکِ همه‌ی اندازه‌گیری‌های یک ویدیو) + measurement_fields (خاصِ هر اندازه‌گیری)
# ==============================================================================

def build_measurement_fields(summary: dict[str, Any]) -> dict[str, Any]:
    # فیلدهای خاصِ یک اندازه‌گیری منفرد (خروجی مدل YOLO روی یک فریم)
    return {
        "measurement_value": summary.get("measurement_value"),
        "measurement_unit":  summary.get("measurement_unit"),
        "measurement_text":  summary.get("measurement_text"),
        "pixel_length":      summary.get("pixel_length"),
        "length_cm":         summary.get("length_cm"),
        "pixels_per_cm":     summary.get("pixels_per_cm"),
    }


def build_internal_row_base(
    video_path: Path,
    session_paths: dict[str, Any],
    classification_result: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    # فیلدهای مشترکِ همه‌ی اندازه‌گیری‌های یک ویدیو (ویو، مسیر سشن، اطمینان طبقه‌بندی)
    return {
        "video_name":             video_path.name,
        "video_path":             str(video_path),
        "session_dir":            relative_to_root(session_paths["session_dir"], output_root),
        "date_folder":            session_paths["date_dir"].name,
        "view_instance":          session_paths["view_name"],
        "detected_view":          classification_result.get("prediction"),
        "classification_source":  classification_result.get("source"),
        "view_confidence":        classification_result.get("confidence"),
    }


def build_public_measurement_row(row: dict[str, Any]) -> dict[str, Any]:
    # internal_row → public_row: فقط فیلدهای لازم برای فرانت (بدون مسیرهای داخلی/دیباگ)
    return {
        "event_name":               row.get("event_name"),
        "event_frame_number":       row.get("event_frame_number"),
        "measurement_name":         row.get("measurement_name"),
        "status":                   row.get("measurement_status"),
        "message":                  row.get("measurement_message"),
        "value":                    row.get("measurement_value"),
        "unit":                     row.get("measurement_unit"),
        "text":                     row.get("measurement_text"),
        "length_cm":                row.get("length_cm"),
        "pixels_per_cm":            row.get("pixels_per_cm"),
        "event_frame_image":        row.get("public_event_image"),
        "measurement_preview_image": row.get("public_preview_image"),
    }



def process_video(
    video_path: Path,
    output_root: Path,
    *,
    patient_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    # --- مرحله ۱: تشخیص ویو ---
    classification_result = run_classification(video_path)
    detected_view         = classification_result["prediction"]

    patient_id = patient_config.get("user_id") if patient_config else None
    if not patient_id:
        patient_id = video_path.parent.name if video_path.parent.name != "." else safe_name(video_path.stem)

    # ساخت پوشه‌های این سشن (internal/public) در pipeline.results
    session_paths = setup_video_session(output_root, video_path, patient_id, classification_result)

    # ویو پشتیبانی‌نشده: یک row با unsupported_view ذخیره و برگردان (بدون ادامه‌ی اندازه‌گیری)
    if detected_view not in VIEW_PIPELINES:
        unsupported_row = {
            "video_name": video_path.name,
            "video_path": str(video_path),
            "measurement_status":  "unsupported_view",
            "measurement_message": f"View '{detected_view}' is not wired in the pipeline yet.",
        }
        save_reports(
            video_path=video_path, session_paths=session_paths,
            patient_id=patient_id, patient_config=patient_config,
            classification_result=classification_result,
            events_result={"event_frames": {}},
            internal_rows=[unsupported_row],
            public_rows=[build_public_measurement_row(unsupported_row)],
            a4c_volume_report=None,
        )
        return [unsupported_row]

    # --- مرحله ۲: استخراج رویدادها ---
    # a4c → ["End Diastol", "End Sistol"] | plax → ["End Diastol", "End Sistol", "LVOT"]
    pipeline_config = VIEW_PIPELINES[detected_view]
    required_events = pipeline_config["events"]

    events_result = extract_events(video_path, session_paths["internal_events_dir"], required_events)
    row_base      = build_internal_row_base(video_path, session_paths, classification_result, output_root)

    # کپی نمودار ECG (نقاط PQRST) به پوشه‌ی public برای نمایش به بیمار در فرانت
    public_ecg_plot = copy_public_file(
        Path(session_paths["internal_events_dir"]) / "ecg_plot.png",
        Path(session_paths["public_events_dir"]) / "ecg_plot.png",
    )

    # محاسبه‌ی مقیاس تصویر (pixels_per_cm) از روی خط‌کش داخل فریم اول
    cap = cv2.VideoCapture(str(video_path))
    ret, original_frame = cap.read()
    cap.release()

    global_pixels_per_cm, global_scale_source = scale_module.estimate_pixels_per_cm_from_bgr(
        original_frame, default_pixels_per_cm=DEFAULT_PIXELS_PER_CM
    )
    scale_debug_path = Path(session_paths["internal_reports_dir"]) / "debug_scale_output.jpg"
    scale_module.visualize_scale_result(
        original_frame, global_pixels_per_cm, global_scale_source,
        save_path=str(scale_debug_path),
    )
    public_scale_debug = copy_public_file(
        scale_debug_path,
        Path(session_paths["public_measurements_dir"]).parent / "scale_debug.jpg",
    )


    # --- مرحله ۳: اندازه‌گیری هر پارامتر روی فریمِ هر رویداد ---
    internal_rows: list[dict] = []
    public_rows:   list[dict] = []
    volume_context = None   # اولین فریم a4c برای محاسبه‌ی حجم در مرحله ۴ نگه داشته می‌شود

    for event_name in required_events:
        frame_number = events_result["event_frames"].get(event_name)
        frame_path   = events_result["saved_frames"].get(event_name)

        if frame_number is None or not frame_path:
            internal_rows.append({**row_base, "event_name": event_name, "measurement_status": "missing_event_frame"})
            continue

        public_event_image = copy_public_file(
            frame_path,
            Path(session_paths["public_events_dir"]) / f"{safe_name(event_name)}.jpg",
        )

        frame_bgr = cv2.imread(str(frame_path))
        if frame_bgr is None:
            continue

        segment_height, segment_width = frame_bgr.shape[:2]

        # اولین فریم a4c رو برای مراحل بعدی (محاسبه‌ی حجم) نگه می‌داریم
        if detected_view == "a4c" and volume_context is None:
            volume_context = {"bgr": frame_bgr, "pixels_per_cm": float(global_pixels_per_cm)}

        # به ازای هر مدل اندازه‌گیری تعریف‌شده برای این رویداد
        for measurement_name in pipeline_config["event_models"].get(event_name, []):
            measurement_dir       = ensure_dir(
                Path(session_paths["internal_measurements_dir"]) / safe_name(event_name) / measurement_name
            )
            annotated_output_path = measurement_dir / f"{measurement_name}.jpg"

            try:
                # می‌ره داخل pipeline.measurement.inference_2d و مدل  مربوطه رو روی فریم اجرا می‌کنه
                measurement_result = run_single_inference(
                    model_weights=measurement_name,
                    file_path=str(frame_path),
                    output_path=str(annotated_output_path),
                    pixels_per_cm=global_pixels_per_cm,
                    segment_width=segment_width,
                    segment_height=segment_height,
                )
                summary = measurement_result["summary"]

                public_preview_image = copy_public_file(
                    measurement_result.get("preview_image"),
                    Path(session_paths["public_measurements_dir"]) / f"{safe_name(event_name)}_{measurement_name}.jpg",
                )

                row = {
                    **row_base,
                    "event_name":          event_name,
                    "event_frame_number":  frame_number,
                    "frame_image":         relative_to_root(frame_path, output_root),
                    "public_event_image":  public_event_image,
                    "one_frame_video":     relative_to_root(video_path, output_root),
                    "measurement_name":    measurement_name,
                    "measurement_status":  measurement_result["status"],
                    "measurement_message": measurement_result["load_message"],
                    "annotated_video":     relative_to_root(measurement_result["output_path"],    output_root),
                    "annotated_preview":   relative_to_root(measurement_result["preview_image"],  output_root),
                    "public_preview_image": public_preview_image,
                    "pred_x1":      summary["pred_x1"],
                    "pred_y1":      summary["pred_y1"],
                    "pred_x2":      summary["pred_x2"],
                    "pred_y2":      summary["pred_y2"],
                    "weights_path": measurement_result["weights_path"],
                    "device":       measurement_result["device"],
                    "scale_source": global_scale_source,
                    **build_measurement_fields(summary),
                }

            except Exception as exc:
                row = {
                    **row_base,
                    "event_name":          event_name,
                    "event_frame_number":  frame_number,
                    "frame_image":         relative_to_root(frame_path, output_root),
                    "public_event_image":  public_event_image,
                    "one_frame_video":     relative_to_root(video_path, output_root),
                    "measurement_name":    measurement_name,
                    "measurement_status":  "error",
                    "measurement_message": str(exc),
                    "pixels_per_cm":       global_pixels_per_cm,
                    "scale_source":        global_scale_source,
                }

            internal_rows.append(row)
            public_rows.append(build_public_measurement_row(row))

    # --- مرحله ۴: محاسبه‌ی حجم دهلیز و بطن — فقط برای ویو a4c ---
    a4c_volume_report = None
    lv_volume_report  = None

    if volume_context is not None and detected_view == "a4c":
        a4c_volume_report = run_a4c_atrial_areas(
            volume_context["bgr"],
            float(volume_context["pixels_per_cm"]),
            output_dir=str(Path(session_paths["internal_reports_dir"]) / "a4c_volume"),
        )

        # اگه وزن مدل سگمنتیشن LV موجود بود → می‌ره داخل measurement.lv_segmentation
        weights_path = Path(__file__).parent / "measurement" / "models" / "best.pth"
        if weights_path.exists():
            lv_volume_report = run_lv_segmentation(
                volume_context["bgr"],
                float(volume_context["pixels_per_cm"]),
                model_path=str(weights_path),
                output_dir=str(Path(session_paths["internal_reports_dir"]) / "lv_volume"),
            )

    # مساحت‌های دهلیز/بطن به تمام سطرهای این ویدیو چسبانده می‌شوند
    # تا بعداً aggregate_and_evaluate_fuzzy مستقیم از همین rowها استفاده کند
    la_area_cm2 = ra_area_cm2 = None
    if a4c_volume_report:
        areas_cm2   = a4c_volume_report.get("areas_cm2", {})
        la_area_cm2 = areas_cm2.get("left_atrium")
        ra_area_cm2 = areas_cm2.get("right_atrium")
    lv_area_cm2 = lv_volume_report.get("area_cm2") if lv_volume_report else None
    for row in internal_rows:
        row["a4c_left_atrium_area_cm2"]  = la_area_cm2
        row["a4c_right_atrium_area_cm2"] = ra_area_cm2
        row["lv_area_cm2"]               = lv_area_cm2

    # --- مرحله ۵ (آخر): ذخیره‌ی همه‌ی گزارش‌های این سشن (internal + public + مونگو) ---
    save_reports(
        video_path=video_path,
        session_paths=session_paths,
        patient_id=patient_id,
        patient_config=patient_config,
        classification_result=classification_result,
        events_result=events_result,
        internal_rows=internal_rows,
        public_rows=public_rows,
        a4c_volume_report=a4c_volume_report,
        lv_volume_report=lv_volume_report,
        extra_public_files={
            "ecg_plot":    public_ecg_plot,       # نمودار PQRST سیگنال قلب
            "scale_debug": public_scale_debug,    # تصویر تشخیص خط‌کش/مقیاس
        },
    )

    return internal_rows

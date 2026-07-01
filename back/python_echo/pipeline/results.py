from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_public_output_root(output_root: Path) -> Path:
    public_root = os.getenv("LARAVEL_PUBLIC_RESULT_PATH")
    if public_root:
        return Path(public_root).expanduser().resolve()
    return output_root.expanduser().resolve()


def path_for_frontend(path_value: str | Path | None) -> str | None:
    # in:  absolute path  → out: relative path for frontend/MongoDB (نسبت به public_root)
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    public_root = os.getenv("LARAVEL_PUBLIC_RESULT_PATH")
    if public_root:
        try:
            return path.relative_to(Path(public_root).expanduser().resolve()).as_posix()
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
    public_root   = get_public_output_root(internal_root)
    date_name     = datetime.now().strftime("%Y-%m-%d")

    parent_folder_name = patient_id or (video_path.parent.name if video_path.parent.name != "." else "default")
    internal_video_dir = ensure_dir(internal_root / safe_name(parent_folder_name))
    public_video_dir   = ensure_dir(public_root   / safe_name(parent_folder_name))
    internal_date_dir  = ensure_dir(internal_video_dir / date_name)
    public_date_dir    = ensure_dir(public_video_dir   / date_name)

    base_view_name = safe_name(detected_view)
    view_name = base_view_name
    index = 2
    while (internal_date_dir / view_name).exists() or (public_date_dir / view_name).exists():
        view_name = f"{base_view_name}_{index}"
        index += 1

    internal_session_dir = ensure_dir(internal_date_dir / view_name)
    public_session_dir   = ensure_dir(public_date_dir   / view_name)
    internal_dir         = ensure_dir(internal_session_dir / "internal")
    public_dir           = public_session_dir

    return {
        "internal_root":              internal_root,
        "public_root":                public_root,
        "video_dir":                  internal_video_dir,
        "date_dir":                   internal_date_dir,
        "session_dir":                internal_session_dir,
        "internal_session_dir":       internal_session_dir,
        "public_session_dir":         public_session_dir,
        "public_video_dir":           public_video_dir,
        "public_date_dir":            public_date_dir,
        "view_name":                  view_name,
        "internal_events_dir":        ensure_dir(internal_dir / "events"),
        "internal_measurements_dir":  ensure_dir(internal_dir / "measurements"),
        "internal_reports_dir":       ensure_dir(internal_dir / "reports"),
        "public_events_dir":          ensure_dir(public_dir / "media" / "events"),
        "public_measurements_dir":    ensure_dir(public_dir / "media" / "measurements"),
        "public_reports_dir":         ensure_dir(public_dir / "reports"),
    }


def copy_public_file(source: str | Path | None, destination: Path, output_root: Path) -> str | None:
    # in:  source (internal path), destination (public path)
    # out: frontend-relative path, or None if source missing
    if not source:
        return None
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source_path, destination)
    return path_for_frontend(destination)


def build_public_classification_result(classification_result: dict[str, Any]) -> dict[str, Any]:
    # in:  full classification_result dict
    # out: {"video_name", "prediction", "source", "confidence", "class_scores"}
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
    # in:  classification_result (prediction already normalized), output_root, patient_id
    # out: session_paths dict  — also writes classification.json to public/reports
    session_paths = build_session_paths(
        output_root, video_path, classification_result["prediction"], patient_id=patient_id
    )
    write_json(
        build_public_classification_result(classification_result),
        Path(session_paths["public_reports_dir"]) / "classification.json",
    )
    return session_paths


def save_final_report_to_mongo(patient_id: str, visit_date: str, report: dict[str, Any]) -> None:
    # in:  patient_id, visit_date, final report dict
    # out: pushes type="final_report" entry into MongoDB visits.{visit_date}
    entry = {
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
    }
    date_field = f"visits.{visit_date}"
    try:
        with _mongo_collection() as coll:
            coll.update_one({"_id": patient_id}, {"$pull": {date_field: {"type": "final_report"}}})
            coll.update_one({"_id": patient_id}, {"$push": {date_field: entry}})
    except Exception as exc:
        print(f"خطا در ذخیره MongoDB: {exc}")


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
) -> None:
    # in:  all video processing results
    # out: measurement_results_full.csv, measurements.csv, result.json, run_report.json → MongoDB
    internal_root = Path(session_paths.get("internal_root", output_root))
    public_root   = Path(session_paths.get("public_root",   output_root))

    internal_csv_path    = Path(session_paths["internal_reports_dir"]) / "measurement_results_full.csv"
    public_csv_path      = Path(session_paths["public_reports_dir"])   / "measurements.csv"
    internal_report_path = Path(session_paths["internal_reports_dir"]) / "run_report.json"
    public_result_path   = Path(session_paths["public_reports_dir"])   / "result.json"

    pd.DataFrame(internal_rows).to_csv(internal_csv_path, index=False)
    pd.DataFrame(public_rows).to_csv(public_csv_path, index=False)

    public_a4c = None
    if a4c_volume_report:
        overlay_src = a4c_volume_report.get("saved_paths", {}).get("overlay_png")
        public_a4c = {
            "pixels_per_cm": a4c_volume_report.get("pixels_per_cm"),
            "areas_cm2":     a4c_volume_report.get("areas_cm2"),
            "overlay_image": copy_public_file(
                overlay_src,
                Path(session_paths["public_measurements_dir"]) / "a4c_atrial_overlay.png",
                public_root,
            ) if overlay_src else None,
        }

    public_lv = None
    if lv_volume_report:
        overlay_src = lv_volume_report.get("saved_paths", {}).get("overlay_png")
        public_lv = {
            "pixels_per_cm": lv_volume_report.get("pixels_per_cm"),
            "area_cm2":      lv_volume_report.get("area_cm2"),
            "overlay_image": copy_public_file(
                overlay_src,
                Path(session_paths["public_measurements_dir"]) / "lv_segmentation_overlay.png",
                public_root,
            ) if overlay_src else None,
        }

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
        },
    }
    write_json(public_result, public_result_path)

    mongo_result = save_public_result_to_mongo(public_result)

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


@contextmanager
def _mongo_collection():
    # out: yields the patients collection; always closes the client
    try:
        from pymongo import MongoClient
    except Exception as exc:
        raise RuntimeError(f"pymongo unavailable: {exc}") from exc
    client = MongoClient(os.getenv("ECHO_MONGO_URI", "mongodb://localhost:27017/"))
    try:
        yield client[os.getenv("ECHO_MONGO_DB", "echo_pipeline")][os.getenv("ECHO_MONGO_COLLECTION", "patients")]
    finally:
        client.close()


def _mongo_upsert_visit(
    patient_id:   str,
    visit_date:   str,
    entry:        dict[str, Any],
    patient_info: dict[str, Any],
    pull_filter:  dict[str, Any],
) -> None:
    # in:  patient_id, visit_date, entry to push, patient_info to $set, pull_filter for dedup
    # out: upserts patient doc, replaces matching entry in visits.{visit_date}
    date_field = f"visits.{visit_date}"
    try:
        with _mongo_collection() as coll:
            coll.update_one({"_id": patient_id},
                            {"$set": {"patient_info": patient_info, "last_updated": datetime.now().isoformat()}},
                            upsert=True)
            coll.update_one({"_id": patient_id}, {"$pull": {date_field: pull_filter}})
            coll.update_one({"_id": patient_id}, {"$push": {date_field: entry}})
    except Exception as exc:
        print(f"MongoDB error: {exc}")


def save_public_result_to_mongo(document: dict[str, Any]) -> dict[str, Any]:
    # in:  public_result dict (study, patient, measurements, ...)
    # out: {"status": "stored"|"skipped"|"error", ...}
    database_name   = os.getenv("ECHO_MONGO_DB",         "echo_pipeline")
    collection_name = os.getenv("ECHO_MONGO_COLLECTION", "patients")

    patient_info  = document.get("patient", {})
    patient_id    = patient_info.get("id", "unknown")
    processed_at  = document.get("study", {}).get("processed_at", "")
    visit_date    = processed_at.split("T")[0] if "T" in processed_at else datetime.now().strftime("%Y-%m-%d")
    view_instance = document.get("study", {}).get("view_instance", "unknown")

    view_result = {
        "view_instance":  view_instance,
        "video_name":     document.get("study", {}).get("video_name"),
        "detected_view":  document.get("study", {}).get("detected_view"),
        "processed_at":   processed_at,
        "session_dir":    document.get("study", {}).get("session_dir"),
        "measurements":   document.get("measurements", []),
        "a4c_volume":     document.get("a4c_volume"),
        "lv_volume":      document.get("lv_volume"),
        "classification": document.get("classification"),
        "files":          document.get("files", {}),
        "updated_at":     datetime.now().isoformat(),
    }

    try:
        with _mongo_collection() as coll:
            date_field = f"visits.{visit_date}"
            coll.update_one({"_id": patient_id},
                            {"$set": {"patient_info": patient_info, "last_updated": datetime.now().isoformat()}},
                            upsert=True)
            coll.update_one({"_id": patient_id}, {"$pull": {date_field: {"view_instance": view_instance}}})
            coll.update_one({"_id": patient_id}, {"$push": {date_field: view_result}})
    except RuntimeError as exc:
        return {"status": "skipped", "reason": str(exc)}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}

    return {
        "status":      "stored",
        "database":    database_name,
        "collection":  collection_name,
        "patient_id":  patient_id,
        "visit_date":  visit_date,
        "view":        view_instance,
    }


def generate_final_patient_report(
    output_root:            Path,
    patient_id:             str,
    visit_date:             str,
    final_report_json_path: Path,
) -> dict[str, Any] | None:
    # in:  output_root, patient_id, visit_date, path to final_report.json
    # out: {llm_report_text, internal_files, public_files, mongodb}  or None if file missing
    from pipeline.llm_report_generator import LLMReportGenerator

    if not final_report_json_path.exists():
        print(f"Final report not found: {final_report_json_path}")
        return None

    with final_report_json_path.open("r", encoding="utf-8") as f:
        final_report_data = json.load(f)

    try:
        generator       = LLMReportGenerator()
        llm_report_text = generator.generate_patient_report(final_report_data)
        html_report     = generator.generate_html_report(llm_report_text, final_report_data)
    except Exception as exc:
        print(f"Error generating LLM report: {exc}")
        llm_report_text = "خطا در تولید گزارش."
        html_report     = "<html><body><p>خطا در تولید گزارش</p></body></html>"

    internal_root     = output_root.expanduser().resolve()
    public_root       = get_public_output_root(internal_root)
    final_report_dir  = ensure_dir(internal_root / safe_name(patient_id) / visit_date / "final_report")

    llm_text_path = final_report_dir / "llm_patient_report.txt"
    llm_html_path = final_report_dir / "patient_report.html"
    llm_text_path.write_text(llm_report_text, encoding="utf-8")
    llm_html_path.write_text(html_report,     encoding="utf-8")

    public_report_dir = ensure_dir(public_root / safe_name(patient_id) / visit_date / "final_report")
    public_text_rel   = copy_public_file(llm_text_path, public_report_dir / "llm_patient_report.txt", public_root)
    public_html_rel   = copy_public_file(llm_html_path, public_report_dir / "patient_report.html",    public_root)

    llm_report_entry = {
        "type":         "llm_final_report",
        "generated_at": datetime.now().isoformat(),
        "report_text":  llm_report_text,
        "files":        {"html": public_html_rel, "text": public_text_rel},
    }
    _mongo_upsert_visit(
        patient_id   = patient_id,
        visit_date   = visit_date,
        entry        = llm_report_entry,
        patient_info = final_report_data.get("patient", {}),
        pull_filter  = {"type": "llm_final_report"},
    )

    return {
        "llm_report_text": llm_report_text,
        "internal_files":  {"text": str(llm_text_path), "html": str(llm_html_path)},
        "public_files":    {"text": public_text_rel,    "html": public_html_rel},
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
    # in:  all pipeline results for one patient/visit
    # out: final_report.json, doctor_report.txt, patient_report.txt, ml_result.json → MongoDB + LLM HTML
    from ai_service.report_generator import build_final_report, save_report

    report     = build_final_report(
        patient_config=patient_config, ml_result=ml_result,
        fuzzy_result=fuzzy_result, echo_rows=all_rows, visit_date=visit_date,
    )
    report_dir = ensure_dir(output_root / safe_name(patient_id) / visit_date / "final_report")
    save_report(report, report_dir, patient_id, visit_date)
    save_final_report_to_mongo(patient_id, visit_date, report)

    try:
        generate_final_patient_report(
            output_root=output_root, patient_id=patient_id,
            visit_date=visit_date, final_report_json_path=report_dir / "final_report.json",
        )
    except Exception as exc:
        import traceback
        print(f"    خطا در تولید گزارش LLM: {exc}")
        traceback.print_exc()


def aggregate_and_evaluate_fuzzy(
    output_root:       Path,
    patient_id:        str,
    visit_date:        str,
    patient_config:    dict[str, Any],
    rows:              list[dict[str, Any]] | None = None,
    summary_csv_path:  Path | None = None,
) -> dict[str, Any] | None:
    # in:  output_root, patient_id, visit_date, patient_config, rows or summary_csv_path
    # out: fuzzy_result dict with llm_prompt, or None if no views processed
    from fazOres.fuzzy import evaluate_patient, aggregate_patient_rows_for_fuzzy

    date_dir = output_root / safe_name(patient_id) / visit_date
    if not date_dir.exists():
        return None

    source_rows = rows
    if source_rows is None and summary_csv_path and summary_csv_path.exists():
        try:
            source_rows = pd.read_csv(summary_csv_path).to_dict(orient="records")
        except Exception as exc:
            print(f"Error reading summary CSV for aggregation: {exc}")
            source_rows = []
    elif source_rows is None:
        source_rows = []

    aggregation      = aggregate_patient_rows_for_fuzzy(source_rows, patient_config)
    aggregated_data  = aggregation["aggregated_data"]
    processed_views  = aggregation["processed_views"]
    rows_used        = aggregation["rows_used"]

    if not processed_views:
        return None

    views_str      = "&".join(processed_views)
    agg_folder_name = f"summary_{views_str}_{datetime.now().strftime('%H_%M')}"
    agg_dir        = ensure_dir(date_dir / agg_folder_name)

    fuzzy_result = evaluate_patient(aggregated_data, patient_name=patient_id, show_plot=agg_dir)

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

    public_root       = get_public_output_root(output_root)
    public_summary_dir = ensure_dir(public_root / safe_name(patient_id) / visit_date / agg_folder_name)
    public_reports_dir = ensure_dir(public_summary_dir / "reports")
    public_media_dir   = ensure_dir(public_summary_dir / "media" / "summary")

    public_files: dict[str, Any] = {
        "fuzzy_summary_json": copy_public_file(internal_summary_json, public_reports_dir / "fuzzy_summary.json", public_root),
        "fuzzy_report_txt":   copy_public_file(internal_report_txt,   public_reports_dir / "fuzzy_report.txt",   public_root),
        "plots": [
            copied for plot_file in sorted(agg_dir.glob("*.png"))
            if (copied := copy_public_file(plot_file, public_media_dir / plot_file.name, public_root))
        ],
    }

    compact_fuzzy = {k: v for k, v in fuzzy_result.items() if k != "llm_prompt"}
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

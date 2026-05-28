
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import math
from pipeline.config import CLASSIFIER_MODEL, RESULT_DIR, VIEW_PIPELINES
from pipeline.measurement import inference_2d as measurement_module
from pipeline.paths import patch_sys_argv_from_windows_command_line, resolve_video_path
from pipeline.processing import process_video
from pipeline.results import aggregate_and_evaluate_fuzzy, ensure_dir, safe_name
import os

BASE_DIR = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Echo pipeline")
    parser.add_argument("video", help="Input video path.")
    parser.add_argument("--output-root", default=str(RESULT_DIR), help="Root folder for outputs.")
    parser.add_argument("--view", choices=sorted(VIEW_PIPELINES.keys()), default=None, help="Force the view and skip classifier.")
    parser.add_argument(
        "--classifier-model",
        default=str(CLASSIFIER_MODEL) if CLASSIFIER_MODEL.exists() else None,
        help="Path to view classifier model.",
    )
    parser.add_argument("--classifier-samples", type=int, default=8, help="Number of sampled frames for classification.")
    parser.add_argument("--one-frame-repeat", type=int, default=8, help="How many times the selected frame should repeat in the temporary AVI.")
    parser.add_argument("--device", default=None, help="Torch device for measurement models.")
    parser.add_argument("--default-pixels-per-cm", type=float, default=12.0, help="Fallback scale when automatic ruler detection fails.")
    parser.add_argument("--patient-id", default=None, help="Optional patient id.")
    parser.add_argument("--patient-name", default=None, help="Optional patient name.")
    return parser


def main() -> None:
    patch_sys_argv_from_windows_command_line()
    args = build_parser().parse_args()

    output_root = ensure_dir(Path(args.output_root).expanduser().resolve())
    input_path = Path(args.video).expanduser().resolve()
    
    all_rows = []
    
    if input_path.is_dir():
        print(f"Processing directory: {input_path}")
        config_file = input_path / "config.json"
        patient_config = {}
        if config_file.exists():
            try:
                with config_file.open("r", encoding="utf-8") as f:
                    patient_config = json.load(f)
                print(f"Loaded config: {patient_config}")
            except Exception as e:
                print(f"Error reading config.json: {e}")
        
        # شناسنامه بیمار همان نام پوشه است
        if "id" not in patient_config:
            patient_config["id"] = input_path.name
            
        video_extensions = {".avi", ".mp4", ".mov", ".mkv", ".wmv"}
        video_files = [f for f in input_path.iterdir() if f.suffix.lower() in video_extensions]
        
        if not video_files:
            print(f"No video files found in {input_path}")
            return

        for video_path in video_files:
            print(f"\n--- Processing video: {video_path.name} ---")
            try:
                # measurement_module = inference_2d 
                rows = process_video(video_path, measurement_module, args, output_root, patient_config=patient_config)
                all_rows.extend(rows)
            except Exception as exc:
                print(f"Error processing {video_path.name}: {exc}")
                all_rows.append({
                    "video_name": video_path.name,
                    "video_path": str(video_path),
                    "patient_id": patient_config.get("id"),
                    "error": str(exc),
                })
        
        visit_date = datetime.now().strftime("%Y-%m-%d")
        summary_csv = output_root / patient_config.get('id') /visit_date/ "pipeline_summary.csv"
        os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
        pd.DataFrame(all_rows).to_csv(summary_csv, index=False)
        print(f"Done. Summary: {summary_csv}")
        print(f"\n--- Running Aggregate Fuzzy Evaluation for {patient_config.get('id')} ---")
        fuzzy_res = aggregate_and_evaluate_fuzzy(
            output_root,
            patient_config.get("id"),
            visit_date,
            patient_config,
            rows=all_rows,
            summary_csv_path=summary_csv,
        )
        if fuzzy_res:
            print(f"Fuzzy Result: {fuzzy_res.get('category')} (Score: {fuzzy_res.get('score')})")
    else: 
        video_path = resolve_video_path(args.video, cwd=BASE_DIR)
        print(f"Processing single video: {video_path}")
        try:
            all_rows = process_video(video_path, measurement_module, args, output_root)
        except Exception as exc:
            all_rows = [
                {
                    "video_name": video_path.name,
                    "video_path": str(video_path),
                    "session_dir": str(output_root / safe_name(video_path.stem)),
                    "error": str(exc),
                }
            ]

    # summary_csv = output_root / patient_config.get('id') / "pipeline_summary.csv"
    # pd.DataFrame(all_rows).to_csv(summary_csv, index=False)
    # print(f"Done. Summary: {summary_csv}")


if __name__ == "__main__":
    main()

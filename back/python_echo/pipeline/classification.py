from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from pipeline.config import CLASSIFIER_MODEL, SUPPORTED_CLASSIFIER_LABELS

DEFAULT_INPUT_SIZE = (224, 224)

# نگاشت نام نما → ایندکس عددی (برای مدل TensorFlow)
LABELS: dict[str, int] = {
    "plax": 0, "psax-av": 1, "psax-mv": 2, "psax-ap": 3,
    "a4c":  4, "a5c":     5, "a3c":     6, "a2c":     7,
}
INDEX_TO_LABEL: dict[int, str] = {v: k for k, v in LABELS.items()}


def normalize_view_label(view_label: str) -> str:
    # in: "A4C " → out: "a4c"
    return str(view_label).strip().lower()


def load_classifier_model():
    # out: (keras Model, CLASSIFIER_MODEL path)  — compile=False, SafeFlatten for legacy compat
    if not CLASSIFIER_MODEL.exists():
        raise FileNotFoundError(f"Classifier model not found: {CLASSIFIER_MODEL}")
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

    try:
        import tensorflow as tf
        from tensorflow.keras.models import load_model
    except Exception as exc:
        raise RuntimeError("TensorFlow is required for automatic view classification.") from exc

    class SafeFlatten(tf.keras.layers.Layer):
        def __init__(self, data_format=None, **kwargs):
            super().__init__(**kwargs)
            self.flatten = tf.keras.layers.Flatten(data_format=data_format)

        def call(self, inputs):
            if isinstance(inputs, list):
                inputs = inputs[0]
            return self.flatten(inputs)

    model = load_model(str(CLASSIFIER_MODEL), custom_objects={"Flatten": SafeFlatten}, compile=False)
    return model, CLASSIFIER_MODEL


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    # in:  BGR / grayscale / BGRA ndarray
    # out: (224, 224, 3) float32 RGB
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.ndim == 3 and frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    resized = cv2.resize(frame, DEFAULT_INPUT_SIZE, interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)


def sample_video_frames(
    video_path:   str | os.PathLike[str],
    sample_count: int = 8,
) -> tuple[list[np.ndarray], list[int], int]:
    # in:  video_path, sample_count (default 8)
    # out: (frames, frame_indices, total_frames)  — uniformly spaced
    resolved = Path(video_path).expanduser().resolve()
    cap = cv2.VideoCapture(str(resolved))
    if not cap.isOpened():
        raise FileNotFoundError(f"Unable to open video: {resolved}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        raise ValueError(f"Video contains no frames: {resolved}")

    indices = sorted(set(int(i) for i in np.linspace(0, total - 1, num=min(sample_count, total), dtype=int)))
    frames, frame_indices = [], []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if ok:
            frames.append(frame)
            frame_indices.append(idx)
    cap.release()

    if not frames:
        raise ValueError("No frame could be sampled for classification.")
    return frames, frame_indices, total


def classify_video(
    video_path:   str | os.PathLike[str],
    sample_count: int = 8,
) -> dict[str, Any]:
    # in:  video_path, sample_count (default 8)
    # out: {video_path, model_path, prediction, confidence, class_scores, frame_results, source}
    model, model_path = load_classifier_model()
    frames, frame_indices, total_frames = sample_video_frames(video_path, sample_count=sample_count)

    batch         = np.asarray([preprocess_frame(f) for f in frames], dtype=np.float32)
    probabilities = np.asarray(model.predict(batch, verbose=0))

    frame_results = [
        {"sample_index": i, "prediction": INDEX_TO_LABEL[int(np.argmax(p))], "confidence": float(np.max(p))}
        for i, p in enumerate(probabilities)
    ]
    averaged_scores = {
        label: float(np.mean(probabilities[:, idx]))
        for idx, label in INDEX_TO_LABEL.items()
    }
    predicted_label = max(averaged_scores, key=averaged_scores.get)

    return {
        "video_path":            str(Path(video_path).expanduser().resolve()),
        "model_path":            str(model_path),
        "sample_count":          len(frames),
        "sampled_frame_indices": frame_indices,
        "total_frames":          total_frames,
        "prediction":            predicted_label,
        "confidence":            float(averaged_scores[predicted_label]),
        "class_scores":          averaged_scores,
        "frame_results":         frame_results,
        "source":                "in_process",
        "classifier_python":     sys.executable,
    }


def run_classification(video_path: Path) -> dict[str, Any]:
    # in:  video_path
    # out: {prediction, confidence, class_scores, ...}  — raises if label unsupported
    result = classify_video(str(video_path))
    label  = normalize_view_label(result["prediction"])
    if label not in SUPPORTED_CLASSIFIER_LABELS:
        raise RuntimeError(f"Classifier returned unexpected label: {result['prediction']}")
    result["prediction"] = label
    return result

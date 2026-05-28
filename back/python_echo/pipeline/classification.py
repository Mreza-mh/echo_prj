from __future__ import annotations
# """
# اگر --view داده شده باشد، مستقیماً یک دیکشنری با source="manual_override" و confidence=1.0 برمی‌گرداند.
# در غیر این صورت مدل TensorFlow (فایل h5.) بارگذاری می‌شود، ۸ فریم از ویدیو نمونه‌برداری می‌شود،
# میانگین امتیازات گرفته می‌شود و بهترین کلاس انتخاب می‌شود.
# خروجی آن یک دیکشنری کامل از نتیجه کلاسیفیکیشن است.
# """


import json
import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd

from pipeline.config import CLASSIFIER_MODEL, SUPPORTED_CLASSIFIER_LABELS

# اندازه ورودی مدل کلاسیفایر
DEFAULT_INPUT_SIZE = (224, 224)

# نگاشت نام نما → ایندکس عددی (برای مدل TensorFlow)
LABELS = {
    "plax": 0,
    "psax-av": 1,
    "psax-mv": 2,
    "psax-ap": 3,
    "a4c": 4,
    "a5c": 5,
    "a3c": 6,
    "a2c": 7,
}

# نگاشت معکوس: ایندکس → نام نما
INDEX_TO_LABEL = {index: label for label, index in LABELS.items()}
# INDEX_TO_LABEL = {0: 'plax', 1: 'psax-av', ..., 7: 'a2c'}


def normalize_view_label(view_label: str) -> str:
    """
    نرمال‌سازی نام نما: حروف کوچک + حذف فاصله اضافی.
    
    ورودی: "A4C " → خروجی: "a4c"
    """
    return str(view_label).strip().lower()


def save_json(data: dict[str, Any], output_path: Path) -> None:
    """
    ذخیره دیکشنری به صورت فایل JSON با indent=2.
    
    ورودی:
        data       : دیکشنری داده
        output_path: مسیر فایل خروجی (مثلاً classification.json)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def build_public_classification_result(classification_result: dict[str, Any]) -> dict[str, Any]:
    # """
    # ساخت نسخه عمومی (خلاصه) از نتیجه کلاسیفیکیشن برای نمایش به کاربر.
    
    # ورودی:
    #     classification_result: خروجی کامل classify_video یا run_classification
    
    # خروجی:
    #     {
    #         "video_name": "dd.avi",
    #         "prediction": "a4c",
    #         "source": "in_process",
    #         "confidence": 0.9859181419014931,
    #         "class_scores": {"plax": 0.0012, "psax-av": 0.0008, ..., "a4c": 0.9859, ...}
    #     }
    # """
    video_path = classification_result.get("video_path")
    return {
        "video_name": Path(video_path).name if video_path else None,
        "prediction": classification_result.get("prediction"),
        "source": classification_result.get("source"),
        "confidence": classification_result.get("confidence"),
        "class_scores": classification_result.get("class_scores", {}),
    }


def save_classification_outputs(output_dir: Path, classification_result: dict[str, Any]) -> None:
    # """
    # ذخیره خروجی‌های کلاسیفیکیشن:
    #   - classification.json : نتیجه عمومی
    #   - classification.csv  : جدول امتیازات هر کلاس
    
    # ورودی:
    #     output_dir          : پوشه public/reports
    #     classification_result: نتیجه کلاسیفیکیشن
    # """
    public_result = build_public_classification_result(classification_result)
    save_json(public_result, output_dir / "classification.json")

    # ساخت یک سطر برای CSV
    row: dict[str, Any] = {
        "video_name": public_result.get("video_name"),      # "dd.avi"
        "prediction": public_result.get("prediction"),      # "a4c"
        "source": public_result.get("source"),              # "in_process"
        "confidence": public_result.get("confidence"),      # 0.9859...
    }
    # اضافه کردن امتیاز هر کلاس به عنوان ستون جداگانه
    for label, score in public_result.get("class_scores", {}).items():
        row[f"class_score_{label}"] = score
        # row["class_score_plax"] = 0.0012
        # row["class_score_a4c"] = 0.9859

    pd.DataFrame([row]).to_csv(output_dir / "classification.csv", index=False)


def resolve_model_path(model_path: str | os.PathLike[str] | None = None) -> Path:
    """
    # پیدا کردن مسیر فایل مدل کلاسیفایر.
    
    # اولویت:
    #   ۱) مسیر داده‌شده توسط کاربر (model_path)
    #   ۲) مسیر پیش‌فرض از config (CLASSIFIER_MODEL)
    
    # ورودی:
    #     model_path: مسیر دلخواه یا None
    
    # خروجی:
    #     Path مسیر معتبر فایل مدل
    
    # خطا:
    #     FileNotFoundError اگر هیچ مسیری معتبر نباشد
    """
    candidates = []
    if model_path:
        candidates.append(Path(model_path).expanduser().resolve())
    candidates.append(CLASSIFIER_MODEL.resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Classifier model not found.")


def load_classifier_model(model_path: str | os.PathLike[str] | None = None):
    # """
    # بارگذاری مدل TensorFlow برای کلاسیفیکیشن نما.
    
    # نکته:
    #   - از SafeFlatten برای سازگاری با مدل‌هایی که لایه Flatten سفارشی دارند استفاده می‌کند.
    #   - compile=False چون فقط برای inference استفاده می‌شود.
    
    # ورودی:
    #     model_path: مسیر فایل مدل (یا None برای استفاده از پیش‌فرض)
    
    # خروجی:
    #     (model, resolved_path)
    #       - model: شیء Keras Model
    #       - resolved_path: مسیر قطعی فایل مدل
    # """
    resolved_path = resolve_model_path(model_path)
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"   # کاهش لاگ‌های TensorFlow

    try:
        import tensorflow as tf
        from tensorflow.keras.models import load_model
    except Exception as exc:
        raise RuntimeError("TensorFlow is required for automatic view classification.") from exc

    # لایه Flatten سفارشی برای سازگاری با مدل‌های قدیمی
    class SafeFlatten(tf.keras.layers.Layer):
        def __init__(self, data_format=None, **kwargs):
            super().__init__(**kwargs)
            self.flatten = tf.keras.layers.Flatten(data_format=data_format)

        def call(self, inputs):
            # اگر ورودی لیست باشد (بعضی مدل‌ها)، اولین عنصر را می‌گیرد
            if isinstance(inputs, list):
                inputs = inputs[0]
            return self.flatten(inputs)

    model = load_model(
        str(resolved_path),
        custom_objects={"Flatten": SafeFlatten},
        compile=False
    )
    return model, resolved_path


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    # """
    # پیش‌پردازش یک فریم برای ورود به مدل کلاسیفایر.
    
    # مراحل:
    #   ۱) تبدیل grayscale یا BGRA به BGR
    #   ۲) تغییر اندازه به 224x224
    #   ۳) تبدیل BGR به RGB
    #   ۴) تبدیل به float32
    
    # ورودی:
    #     frame: np.ndarray با ابعاد مختلف
    
    # خروجی:
    #     np.ndarray با shape (224, 224, 3) و dtype float32
    # """
    
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.ndim == 3 and frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    resized = cv2.resize(frame, DEFAULT_INPUT_SIZE, interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32)


def sample_video_frames(
    video_path: str | os.PathLike[str],
    sample_count: int = 8
) -> tuple[list[np.ndarray], list[int], int]:
    # """
    # نمونه‌برداری یکنواخت n فریم از ویدیو.
    
    # ورودی:
    #     video_path  : مسیر ویدیو
    #     sample_count: تعداد فریم‌های نمونه (پیش‌فرض ۸)
    
    # خروجی:
    #     (frames, frame_indices, total_frames)
    #       - frames       : لیست n عدد np.ndarray
    #       - frame_indices: لیست شماره فریم‌های نمونه‌برداری‌شده
    #       - total_frames : کل فریم‌های ویدیو
    # """
    resolved_video = Path(video_path).expanduser().resolve()
    capture = cv2.VideoCapture(str(resolved_video))
    if not capture.isOpened():
        raise FileNotFoundError(f"Unable to open video: {resolved_video}")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    # total_frames = 102 (برای dd.avi)

    if total_frames <= 0:
        capture.release()
        raise ValueError(f"Video contains no frames: {resolved_video}")

    # انتخاب ایندکس‌های یکنواخت
    indices = np.linspace(0, total_frames - 1, num=min(sample_count, total_frames), dtype=int)
    # indices = [0, 14, 28, 43, 57, 71, 85, 99]  (۸ فریم)
    indices = sorted(set(int(index) for index in indices))

    frames: list[np.ndarray] = []
    frame_indices: list[int] = []
    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if ok:
            frames.append(frame)
            frame_indices.append(index)

    capture.release()
    if not frames:
        raise ValueError("No frame could be sampled for classification.")
    return frames, frame_indices, total_frames


def classify_video(
    video_path: str | os.PathLike[str],
    model_path: str | os.PathLike[str] | None = None,
    sample_count: int = 8,
) -> dict[str, Any]:
    # """
    # کلاسیفیکیشن کامل یک ویدیو: بارگذاری مدل، نمونه‌برداری، پیش‌بینی.
    
    # مراحل:
    #   ۱) بارگذاری مدل
    #   ۲) نمونه‌برداری ۸ فریم
    #   ۳) پیش‌پردازش و batch inference
    #   ۴) میانگین‌گیری امتیازات
    #   ۵) انتخاب بهترین کلاس
    
    # ورودی:
    #     video_path  : مسیر ویدیو
    #     model_path  : مسیر مدل (None = پیش‌فرض)
    #     sample_count: تعداد فریم نمونه
    
    # خروجی:
    #     دیکشنری کامل نتیجه کلاسیفیکیشن (مقادیر واقعی از لاگ):
    #     {
    #         "video_path": "C:\\Users\\SiBIRAN\\Desktop\\prj\\404445623\\dd.avi",
    #         "model_path": "C:\\...\\mymodel_echocv_500-500-8_adam_16_0.9394.h5",
    #         "sample_count": 8,
    #         "sampled_frame_indices": [0, 14, 28, 43, 57, 71, 85, 99],
    #         "total_frames": 102,
    #         "prediction": "a4c",
    #         "confidence": 0.9859181419014931,
    #         "class_scores": {
    #             "plax": 0.0012, "psax-av": 0.0008, "psax-mv": 0.0011,
    #             "psax-ap": 0.0009, "a4c": 0.9859, "a5c": 0.0034,
    #             "a3c": 0.0021, "a2c": 0.0046
    #         },
    #         "frame_results": [
    #             {"sample_index": 0, "prediction": "a4c", "confidence": 0.99},
    #             ...
    #         ],
    #         "source": "in_process",
    #         "classifier_python": "C:\\Users\\...\\python.exe"
    #     }
    # """
    # بارگذاری مدل
    model, resolved_model_path = load_classifier_model(model_path)

    # نمونه‌برداری فریم‌ها
    frames, frame_indices, total_frames = sample_video_frames(video_path, sample_count=sample_count)

    # پیش‌پردازش و ایجاد batch
    batch = np.asarray([preprocess_frame(frame) for frame in frames], dtype=np.float32)
    # batch.shape = (8, 224, 224, 3)

    # پیش‌بینی
    probabilities = np.asarray(model.predict(batch, verbose=0))
    # probabilities.shape = (8, 8)  — ۸ فریم، هر کدام ۸ کلاس

    # نتیجه هر فریم جداگانه
    frame_results = []
    for sample_index, probs in enumerate(probabilities):
        predicted_index = int(np.argmax(probs))
        frame_results.append({
            "sample_index": sample_index,
            "prediction": INDEX_TO_LABEL[predicted_index],
            "confidence": float(np.max(probs)),
        })

    # میانگین‌گیری امتیازات روی تمام فریم‌ها
    averaged_scores = {
        label: float(np.mean([float(item[index]) for item in probabilities]))
        for index, label in INDEX_TO_LABEL.items()
    }
    # averaged_scores = {"plax": 0.0012, ..., "a4c": 0.9859, ...}

    # بهترین کلاس
    predicted_label = max(averaged_scores, key=averaged_scores.get)
    # predicted_label = "a4c"

    return {
        "video_path": str(Path(video_path).expanduser().resolve()),
        "model_path": str(resolved_model_path),
        "sample_count": len(frames),
        "sampled_frame_indices": frame_indices,
        "total_frames": total_frames,
        "prediction": predicted_label,
        "confidence": float(averaged_scores[predicted_label]),
        "class_scores": averaged_scores,
        "frame_results": frame_results,
        "source": "in_process",
        "classifier_python": sys.executable,
    }


def run_classification(
    video_path: Path,
    *,
    manual_view: str | None,            # None (اگر کاربر --view ندهد)
    classifier_model: str | None,       # مسیر مدل یا None
    classifier_samples: int,            # 8
) -> dict[str, Any]:
    # """
    # تابع اصلی کلاسیفیکیشن: تصمیم‌گیری بین حالت دستی و خودکار.
    
    # ورودی:
    #     video_path       : مسیر ویدیو
    #     manual_view      : اگر کاربر --view بدهد، نام نما (مثلاً "a4c")
    #     classifier_model : مسیر مدل کلاسیفایر
    #     classifier_samples: تعداد فریم نمونه (۸)
    
    # خروجی:
    #     دیکشنری کامل نتیجه کلاسیفیکیشن
    # """
    # ----- حالت دستی -----
    if manual_view:
        label = normalize_view_label(manual_view)
        return {
            "video_path": str(video_path),
            "prediction": label,
            "source": "manual_override",                    # منبع = دستی
            "model_path": (
                str(resolve_model_path(classifier_model))
                if classifier_model or CLASSIFIER_MODEL.exists()
                else None
            ),
            "sample_count": 0,
            "sampled_frame_indices": [],
            "total_frames": 0,
            "confidence": 1.0,                              # اطمینان ۱۰۰٪
            "class_scores": {label: 1.0},                   # فقط کلاس انتخاب‌شده
            "frame_results": [],
        }

    # ----- حالت خودکار (با مدل) -----
    result = classify_video(
        str(video_path),
        model_path=classifier_model,
        sample_count=classifier_samples
    )
    # result = {...} (خروجی classify_video)

    # نرمال‌سازی نام نما
    label = normalize_view_label(result["prediction"])
    # label = "a4c"

    # بررسی اینکه نما جزو نماهای پشتیبانی‌شده باشد
    if label not in SUPPORTED_CLASSIFIER_LABELS:
        # SUPPORTED_CLASSIFIER_LABELS = {"plax", "psax-av", "psax-mv", "psax-ap", "a2c", "a3c", "a4c", "a5c"}
        raise RuntimeError(f"Classifier returned unexpected label: {result['prediction']}")

    result["prediction"] = label
    return result
    # خروجی نهایی:
    # {
    #     "video_path": "C:\\Users\\...\\dd.avi",
    #     "model_path": "C:\\...\\mymodel_echocv_..._0.9394.h5",
    #     "sample_count": 8,
    #     "sampled_frame_indices": [0, 14, 28, 43, 57, 71, 85, 99],
    #     "total_frames": 102,
    #     "prediction": "a4c",
    #     "confidence": 0.9859181419014931,
    #     "class_scores": {"plax": 0.0012, ..., "a4c": 0.9859, ...},
    #     "frame_results": [...],
    #     "source": "in_process",
    #     "classifier_python": "C:\\Users\\...\\python.exe"
    # }
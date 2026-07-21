import os
from pathlib import Path
from dataclasses import dataclass
from argparse import ArgumentParser

import cv2
import numpy as np
import pandas as pd
import torch
from torchvision.models.segmentation import deeplabv3_resnet50

_CURRENT = Path(__file__).resolve().parent
# _CURRENT = Path("C:/Users/.../pipeline/measurement")

_PROJECT_ROOT = _CURRENT.parent.parent
# _PROJECT_ROOT = Path("C:/Users/.../")

from pipeline.measurement.scale import length_cm_from_model_line

# مسیر قدیمی وزن‌ها (برای سازگاری با نسخه‌های قبلی)
_LEGACY_WEIGHTS = _PROJECT_ROOT / "measurements-main" / "Measurement" / "weights" / "2D_models"

# لیست مدل‌های پشتیبانی‌شده
SUPPORTED_MODEL_WEIGHTS = (
    "ivs",         # Intraventricular Septum (سپتوم بین بطنی)
    "lvid",        # Left Ventricular Internal Diameter (قطر داخلی بطن چپ)
    "lvpw",        # Left Ventricular Posterior Wall (دیواره خلفی بطن چپ)
    "aorta",       # Aorta (آئورت)
    "aortic_root", # Aortic Root (ریشه آئورت)
    "rv_base",     # Right Ventricle Base (قاعده بطن راست)
)

# اندازه ورودی مدل DeepLabV3+
MODEL_INPUT_SIZE = (640, 480)


# ==============================================================================
# بارگذاری مدل (device, weights, backbone)
# ==============================================================================

@dataclass
class MeasurementRunner:
    """
    داده‌کلاس نگهدارنده وضعیت یک مدل اندازه‌گیری.
    
    فیلدها:
        measurement_name: نام مدل (مثلاً "rv_base")
        weights_path    : مسیر فایل وزن‌ها (ckpt.)
        device          : دستگاه محاسباتی ("cpu" یا "cuda:0")
        is_stub         : آیا مدل واقعی نیست؟ (همیشه False)
        model           : شیء PyTorch مدل (DeepLabV3+)
        load_status     : وضعیت بارگذاری ("ok" یا "partial")
        load_message    : پیام بارگذاری
    """
    measurement_name: str
    weights_path: Path
    device: str
    is_stub: bool
    model: object | None
    load_status: str
    load_message: str


def resolve_device(device: str | None = None) -> str:
    """
    تعیین دستگاه محاسباتی.
    
    ورودی:
        device: "cuda:0", "cpu", یا None
    
    خروجی:
        اگر None باشد: "cuda:0" (اگر GPU موجود باشد) وگرنه "cpu"
        در ویندوز (لاگ واقعی): "cpu" (چون TensorFlow GPU روی ویندوز پشتیبانی نمی‌شود)
    """
    if device:
        return device
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def resolve_weights_path(
    model_weights: str,                              # "rv_base"
    weights_dir: str | os.PathLike[str] | None = None
) -> Path:
    """
    پیدا کردن مسیر فایل وزن‌های یک مدل.
    
    اولویت جستجو:
      ۱) weights_dir (اگر داده شده باشد)
      ۲) pipeline/measurement/weights/2D_models/
      ۳) مسیر قدیمی (_LEGACY_WEIGHTS)
    
    ورودی:
        model_weights: نام مدل (مثلاً "rv_base")
        weights_dir  : پوشه سفارشی وزن‌ها یا None
    
    خروجی:
        مسیر فایل (مثلاً Path(".../rv_base_weights.ckpt"))
    
    خطا:
        FileNotFoundError اگر فایل وزن‌ها پیدا نشد
    """
    candidates: list[Path] = []
    if weights_dir:
        candidates.append(Path(weights_dir))
    candidates.append(_CURRENT / "weights" / "2D_models")
    if _LEGACY_WEIGHTS.exists():
        candidates.append(_LEGACY_WEIGHTS)

    for base_dir in candidates:
        weights_path = base_dir / f"{model_weights}_weights.ckpt"
        # مثلاً: ".../2D_models/rv_base_weights.ckpt"
        if weights_path.is_file():
            return weights_path.resolve()

    raise FileNotFoundError(f"Measurement weights not found for '{model_weights}'.")


def build_backbone():
    """
    ساخت مدل DeepLabV3+ با backbone ResNet50.
    
    خروجی:
        مدل با ۲ کلاس خروجی 
    
    نکته:
        سه حالت try/except برای سازگاری با نسخه‌های مختلف torchvision
    """
    try:
        # نسخه جدید torchvision
        return deeplabv3_resnet50(weights=None, weights_backbone=None, num_classes=2)
    except TypeError:
        try:
            # نسخه قدیمی‌تر
            return deeplabv3_resnet50(pretrained=False, progress=False, num_classes=2)
        except TypeError:
            # قدیمی‌ترین نسخه
            return deeplabv3_resnet50(num_classes=2)


def normalize_state_dict(raw_weights) -> dict:
    """
    نرمال‌سازی state_dict بارگذاری‌شده.
    
    برخی فایل‌های ckpt کلیدها را با پیشوند "m." ذخیره می‌کنند.
    این تابع آن پیشوند را حذف می‌کند.
    
    ورودی:
        raw_weights: دیکشنری وزن‌های بارگذاری‌شده (یا شامل کلید "state_dict")
    
    خروجی:
        دیکشنری نرمال‌شده
    """
    # اگر فایل شامل کلید "state_dict" باشد، آن را استخراج کن
    if isinstance(raw_weights, dict) and "state_dict" in raw_weights and isinstance(raw_weights["state_dict"], dict):
        raw_weights = raw_weights["state_dict"]

    normalized = {}
    for key, value in raw_weights.items():
        # حذف پیشوند "m." از کلیدها
        new_key = key[2:] if key.startswith("m.") else key
        normalized[new_key] = value
    return normalized


def load_measurement_runner(
    model_weights: str,                              # "rv_base"
    weights_dir: str | os.PathLike[str] | None = None,
    device: str | None = None
) -> MeasurementRunner:
    """
    بارگذاری کامل یک مدل اندازه‌گیری.
    
    مراحل:
      ۱) تعیین دستگاه (cpu/cuda)
      ۲) پیدا کردن مسیر فایل وزن‌ها
      ۳) بارگذاری وزن‌ها با torch.load
      ۴) نرمال‌سازی state_dict
      ۵) ساخت مدل DeepLabV3+
      ۶) بارگذاری وزن‌ها در مدل
      ۷) انتقال مدل به دستگاه و تنظیم حالت eval
    
    ورودی:
        model_weights: نام مدل
        weights_dir  : پوشه وزن‌ها
        device       : دستگاه محاسباتی
    
    خروجی:
        MeasurementRunner با مدل بارگذاری‌شده و آماده inference
    """
    resolved_device = resolve_device(device)                        # "cpu"
    weights_path = resolve_weights_path(model_weights, weights_dir=weights_dir)
    # weights_path = Path(".../rv_base_weights.ckpt")

    # بارگذاری وزن‌ها از فایل
    raw_weights = torch.load(str(weights_path), map_location=resolved_device)
    state_dict = normalize_state_dict(raw_weights)

    # ساخت مدل
    model = build_backbone()                                        # DeepLabV3+ (ResNet50, 2 کلاس)

    # بارگذاری وزن‌ها در مدل (strict=False → فقط لایه‌های موجود)
    load_result = model.load_state_dict(state_dict, strict=False)
    model = model.to(resolved_device)                               # انتقال به CPU
    model.eval()                                                    # حالت ارزیابی

    # بررسی وضعیت بارگذاری
    load_status = "ok" if not (load_result.missing_keys or load_result.unexpected_keys) else "partial"
    load_message = "Weights loaded successfully."

    return MeasurementRunner(
        measurement_name=model_weights,    # "rv_base"
        weights_path=weights_path,
        device=resolved_device,            # "cpu"
        is_stub=False,
        model=model,
        load_status=load_status,           # "ok"
        load_message=load_message,         # "Weights loaded successfully."
    )


# ==============================================================================
# پیش‌پردازش تصویر ورودی → تنسور
# ==============================================================================

def load_image_frame(file_path: str | os.PathLike[str]) -> list[np.ndarray]:
    """
    خواندن یک تصویر و تغییر اندازه به 640x480.
    
    ورودی:
        file_path: مسیر فایل تصویر (مثلاً ".../frame_0060.jpg")
    
    خروجی:
        لیست تک‌عضوی شامل np.ndarray با shape (480, 640, 3)
    """
    resolved_path = Path(file_path).expanduser().resolve()
    frame = cv2.imread(str(resolved_path))                           # BGR
    if frame is None:
        raise FileNotFoundError(f"Unable to read image: {resolved_path}")
    resized = cv2.resize(frame, MODEL_INPUT_SIZE, interpolation=cv2.INTER_AREA)
    # resized.shape = (480, 640, 3)
    return [resized]                                                 # لیست برای سازگاری با batch


def frames_to_tensor(frames: list[np.ndarray], device: str) -> torch.Tensor:
    """
    تبدیل لیست فریم‌ها به تنسور PyTorch.
    
    مراحل:
      ۱) تبدیل به np.array و نرمال‌سازی (تقسیم بر ۲۵۵)
      ۲) انتقال به دستگاه
      ۳) تغییر چینش ابعاد: (B, H, W, C) → (B, C, H, W)
    
    ورودی:
        frames: لیست فریم‌ها (هر کدام shape: H, W, 3)
        device: "cpu" یا "cuda:0"
    
    خروجی:
        torch.Tensor با shape (1, 3, 480, 640) و dtype float32
    """
    input_tensor = torch.tensor(np.asarray(frames)).float() / 255.0
    # input_tensor.shape = (1, 480, 640, 3)
    return input_tensor.to(device).permute(0, 3, 1, 2)
    # خروجی: (1, 3, 480, 640)


# ==============================================================================
# اجرای مدل و تبدیل خروجی segmentation به مختصات دو نقطه
# ==============================================================================

def segmentation_to_coordinates(
    logits: torch.Tensor,                # (1, 2, 480, 640) — ۲ کانال، هر کدام probability map
    normalize: bool = True,
    order: str = "YX"
) -> torch.Tensor:
    """
    تبدیل probability map حاصل از segmentation به مختصات نقاط کلیدی.

    منطق (weighted centroid — مشابه مرکز جرم در فیزیک):
        x_center = sum(x * p) / sum(p)
        y_center = sum(y * p) / sum(p)

    ورودی:
        logits   : تنسور با shape (..., n_points, H, W) — بعد از sigmoid، مقادیر [0,1]
        normalize: اگر True، مختصات در بازه [0,1] نرمال‌سازی می‌شوند
        order    : "YX" → [y, x]  یا  "XY" → [x, y]

    خروجی:
        تنسور با shape (..., n_points, 2)
        مثلاً: shape (1, 2, 2) = [[[158, 266], [299, 268]]]
    """
    # ساخت ماتریس‌های مختصات سطری و ستونی
    predictions_rows, predictions_cols = torch.meshgrid(
        torch.arange(logits.shape[-2], device=logits.device),   # [0, 1, ..., 479]  (H)
        torch.arange(logits.shape[-1], device=logits.device),   # [0, 1, ..., 639]  (W)
        indexing="ij",
    )

    # محاسبه weighted sum
    predictions_rows = predictions_rows * logits                # y_weighted
    predictions_cols = predictions_cols * logits                # x_weighted

    # جمع در راستای H و W → centroid
    predictions_rows = predictions_rows.sum(dim=(-2, -1)) / (logits.sum(dim=(-2, -1)) + 1e-8)
    predictions_cols = predictions_cols.sum(dim=(-2, -1)) / (logits.sum(dim=(-2, -1)) + 1e-8)

    # نرمال‌سازی (اختیاری)
    if normalize:
        predictions_rows = predictions_rows / logits.shape[-2]  # تقسیم بر H
        predictions_cols = predictions_cols / logits.shape[-1]  # تقسیم بر W

    # انتخاب ترتیب خروجی
    if order == "YX":
        return torch.stack([predictions_rows, predictions_cols], dim=-1)
    if order == "XY":
        return torch.stack([predictions_cols, predictions_rows], dim=-1)

    raise ValueError(f"Invalid order: {order}")


def forward_pass(runner: MeasurementRunner, inputs: torch.Tensor) -> torch.Tensor:
    """
    اجرای forward مدل و تبدیل logits به مختصات.
    
    مراحل:
      ۱) اجرای مدل → logits خام
      ۲) اعمال sigmoid → احتمال
      ۳) تبدیل probability map به مختصات با segmentation_to_coordinates
    
    ورودی:
        runner: MeasurementRunner با مدل بارگذاری‌شده
        inputs: تنسور ورودی (1, 3, 480, 640)
    
    خروجی:
        تنسور مختصات با shape (1, 2, 2) — دو نقطه (x1,y1) و (x2,y2)
    """
    logits = runner.model(inputs)["out"]                             # (1, 2, 480, 640)
    logits = torch.sigmoid(logits)                                   # تبدیل به احتمال [0,1]
    return segmentation_to_coordinates(logits, normalize=False, order="XY")
    # خروجی: (1, 2, 2) — مختصات دو نقطه به ترتیب XY


def predict_coordinates(runner: MeasurementRunner, input_tensor: torch.Tensor) -> np.ndarray:
    """
    پیش‌بینی مختصات بدون گرادیان.
    
    ورودی:
        runner     : مدل بارگذاری‌شده
        input_tensor: تنسور ورودی
    
    خروجی:
        np.ndarray با shape (1, 2, 2)
        مثلاً [[[158, 266], [299, 268]]]
    """
    with torch.no_grad():
        prediction = forward_pass(runner, input_tensor)
    return prediction.cpu().numpy()


# ==============================================================================
# ترسیم و ذخیره‌ی نتیجه (annotate + CSV)
# ==============================================================================

def compute_pixel_length(x1: int, y1: int, x2: int, y2: int) -> float:
    """
    محاسبه فاصله اقلیدسی بین دو نقطه.
    
    ورودی: (158, 266) و (299, 268)
    خروجی: 141.01418368376991
    """
    return float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))


def format_measurement_text(
    pixel_length: float,     # 141.014...
    x1: int, y1: int,        # 158, 266
    x2: int, y2: int,        # 299, 268
    *,
    length_cm: float | None = None   # 4.714957972982647
) -> str:
    """
    ساخت رشته متن اندازه‌گیری برای نمایش روی تصویر.
    
    خروجی:
        "Length: 141.01 px  (158,266)-(299,268)  |  4.715 cm"
    """
    base = f"Length: {pixel_length:.2f} px  ({x1},{y1})-({x2},{y2})"
    if length_cm is not None:
        return f"{base}  |  {length_cm:.3f} cm"
    return base


def make_annotated_frame(
    frame_tensor: torch.Tensor,          # (3, 480, 640)
    prediction: np.ndarray,              # [[[158, 266], [299, 268]]]
    *,
    pixels_per_cm: float | None = None,  # 28.6
    segment_width: int | None = None,    # 612
    segment_height: int | None = None,   # 507
):
    """
    ساخت تصویر حاشیه‌نویسی‌شده با نقاط و خط اندازه‌گیری.
    
    عناصر رسم‌شده:
      - دو دایره آبی روی نقاط ابتدا و انتها
      - خط آبی بین دو نقطه
      - مستطیل مشکی با متن اندازه‌گیری
      - تبدیل طول به cm با در نظر گرفتن ابعاد واقعی تصویر
    
    ورودی:
        frame_tensor  : تنسور تصویر (3, 480, 640)
        prediction    : مختصات پیش‌بینی‌شده
        pixels_per_cm : مقیاس
        segment_width : عرض تصویر واقعی
        segment_height: ارتفاع تصویر واقعی
    
    خروجی:
        (frame, x1, y1, x2, y2, pixel_length, length_cm, measurement_text)
    """
    # تبدیل تنسور به تصویر numpy
    frame = frame_tensor.permute(1, 2, 0).cpu().numpy()             # (480, 640, 3)
    frame = (np.clip(frame, 0, 1) * 255).astype(np.uint8)           # [0, 255]

    # استخراج مختصات
    x1, y1 = int(prediction[0][0]), int(prediction[0][1])           # 158, 266
    x2, y2 = int(prediction[1][0]), int(prediction[1][1])           # 299, 268

    # محاسبه طول پیکسلی
    pixel_length = compute_pixel_length(x1, y1, x2, y2)             # 141.014...

    # محاسبه طول به سانتی‌متر (با نگاشت به ابعاد واقعی)
    length_cm: float | None = None
    if pixels_per_cm is not None and pixels_per_cm > 0 and segment_width is not None and segment_height is not None:
        length_cm = length_cm_from_model_line(
            float(x1), float(y1), float(x2), float(y2),
            pixels_per_cm=pixels_per_cm,          # 28.6
            segment_width=int(segment_width),     # 612
            segment_height=int(segment_height),   # 507
        )
        # length_cm = 4.714957972982647

    # ساخت متن
    measurement_text = format_measurement_text(pixel_length, x1, y1, x2, y2, length_cm=length_cm)
    # "Length: 141.01 px  (158,266)-(299,268)  |  4.715 cm"

    # رسم روی تصویر
    cv2.circle(frame, (x1, y1), 4, (135, 206, 235), -1)            # دایره آبی
    cv2.circle(frame, (x2, y2), 4, (135, 206, 235), -1)            # دایره آبی
    cv2.line(frame, (x1, y1), (x2, y2), (135, 206, 235), 2)       # خط آبی
    cv2.rectangle(frame, (12, 12), (260, 48), (0, 0, 0), -1)       # پس‌زمینه مشکی
    cv2.putText(frame, measurement_text, (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

    return frame, x1, y1, x2, y2, pixel_length, length_cm, measurement_text


def write_annotated_image(
    output_path: str | os.PathLike[str],          # ".../rv_base.jpg"
    input_tensor: torch.Tensor,                   # (1, 3, 480, 640)
    predictions: np.ndarray,                      # (1, 2, 2)
    *,
    pixels_per_cm: float | None = None,
    segment_width: int | None = None,
    segment_height: int | None = None,
) -> pd.DataFrame:
    """
    ذخیره تصویر حاشیه‌نویسی‌شده و برگرداندن DataFrame.
    
    خروجی:
        DataFrame یک‌سطره شامل مختصات، طول پیکسل، طول cm، و متن
    """
    resolved_output = Path(output_path).expanduser().resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    annotated, x1, y1, x2, y2, pixel_length, length_cm, measurement_text = make_annotated_frame(
        input_tensor[0], predictions[0],          # فقط اولین (و تنها) فریم
        pixels_per_cm=pixels_per_cm,
        segment_width=segment_width,
        segment_height=segment_height,
    )

    cv2.imwrite(str(resolved_output), annotated)                    # ذخیره تصویر

    # تعیین واحد و مقدار
    unit = "cm" if length_cm is not None else "px"
    value = float(length_cm) if length_cm is not None else float(pixel_length)

    row = {
        "frame_number": 0,
        "pred_x1": x1,                            # 158
        "pred_y1": y1,                            # 266
        "pred_x2": x2,                            # 299
        "pred_y2": y2,                            # 268
        "pixel_length": pixel_length,             # 141.014...
        "length_cm": length_cm,                   # 4.714...
        "pixels_per_cm": pixels_per_cm,           # 28.6
        "measurement_value": value,               # 4.714...
        "measurement_unit": unit,                 # "cm"
        "measurement_text": measurement_text,     # "Length: 141.01 px  ...  |  4.715 cm"
    }
    return pd.DataFrame([row])


# ==============================================================================
# run_single_inference — نقطه‌ی ورود این ماژول؛ processing.process_video برای هر
# ترکیب (رویداد × مدل) یک‌بار همینو صدا می‌زنه
# ==============================================================================

def run_single_inference(
    model_weights: str,                              # "rv_base"
    file_path: str | os.PathLike[str],               # ".../frame_0060.jpg"
    output_path: str | os.PathLike[str],             # ".../rv_base.jpg"
    weights_dir: str | os.PathLike[str] | None = None,
    device: str | None = None,
    *,
    pixels_per_cm: float | None = None,              # 28.6
    segment_width: int | None = None,                # 612
    segment_height: int | None = None,               # 507
) -> dict:
    """
    اجرای کامل یک مدل اندازه‌گیری روی یک تصویر.
    
    مراحل:
      ۱) بارگذاری مدل و وزن‌ها
      ۲) خواندن و پیش‌پردازش تصویر
      ۳) پیش‌بینی مختصات
      ۴) رسم و ذخیره تصویر حاشیه‌نویسی‌شده

    ورودی:
        model_weights : نام مدل
        file_path     : مسیر تصویر ورودی
        output_path   : مسیر تصویر خروجی
        weights_dir   : پوشه وزن‌ها
        device        : دستگاه محاسباتی
        pixels_per_cm : مقیاس
        segment_width : عرض تصویر واقعی
        segment_height: ارتفاع تصویر واقعی
    
    خروجی:
        دیکشنری کامل نتیجه (مقادیر واقعی از لاگ):
        {
            "measurement_name": "rv_base",
            "status": "ok",
            "load_message": "Weights loaded successfully.",
            "device": "cpu",
            "weights_path": "C:\\Users\\...\\rv_base_weights.ckpt",
            "input_path": "C:\\Users\\...\\frame_0060.jpg",
            "output_path": "C:\\Users\\...\\rv_base.jpg",
            "preview_image": "C:\\Users\\...\\rv_base.jpg",
            "frame_count": 1,
            "summary": {
                "frame_number": 0,
                "pred_x1": 158, "pred_y1": 266,
                "pred_x2": 299, "pred_y2": 268,
                "pixel_length": 141.01418368376991,
                "length_cm": 4.714957972982647,
                "pixels_per_cm": 28.6,
                "measurement_value": 4.714957972982647,
                "measurement_unit": "cm",
                "measurement_text": "Length: 141.01 px  (158,266)-(299,268)  |  4.715 cm"
            }
        }
    """
    # --- مرحله ۱: می‌ره داخل load_measurement_runner و مدل مربوط به model_weights رو لود می‌کنه (هر بار از صفر) ---
    runner = load_measurement_runner(model_weights, weights_dir=weights_dir, device=device)

    # --- مرحله ۲: خواندن فریم تصویر و resize به سایز ورودی مدل ---
    frames = load_image_frame(file_path)                            # [(480, 640, 3)]

    # --- مرحله ۳: تبدیل فریم به تنسور PyTorch ---
    input_tensor = frames_to_tensor(frames, device=runner.device)   # (1, 3, 480, 640)

    # --- مرحله ۴: اجرای forward pass مدل → مختصات دو نقطه‌ی خط اندازه‌گیری ---
    predictions = predict_coordinates(runner, input_tensor)         # (1, 2, 2)

    # --- مرحله ۵: می‌ره داخل write_annotated_image → تصویر annotate شده رو می‌سازه و ذخیره می‌کنه ---
    dataframe = write_annotated_image(
        output_path, input_tensor, predictions,
        pixels_per_cm=pixels_per_cm,
        segment_width=segment_width,
        segment_height=segment_height,
    )
    # dataframe: DataFrame یک‌سطره

    resolved_output = Path(output_path).expanduser().resolve()
    first_row = dataframe.iloc[0].to_dict()

    return {
        "measurement_name": model_weights,
        "status": runner.load_status,                               # "ok"
        "load_message": runner.load_message,                        # "Weights loaded successfully."
        "device": runner.device,                                    # "cpu"
        "weights_path": str(runner.weights_path),
        "input_path": str(Path(file_path).expanduser().resolve()),
        "output_path": str(resolved_output),
        "preview_image": str(resolved_output),                      # همان output_path
        "frame_count": 1,
        "summary": first_row,
    }
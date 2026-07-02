"""
Left Ventricle (LV) segmentation and area calculation (cm²).

Uses a U-Net++ model (timm-efficientnet-b4 encoder) to segment the LV
in A4C/A2C views. Entry point: `run_lv_segmentation`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import segmentation_models_pytorch as smp

from pipeline.measurement.scale import pixel_area_to_cm2

# ابعاد ورودی مدل (عرض، ارتفاع) — تصویر قبل از inference به این اندازه resize می‌شود
MODEL_INPUT_SIZE = (256, 256)

# آستانه‌ی تبدیل خروجی sigmoid به ماسک باینری؛ مقدار پایین یعنی recall بالاتر
PROB_THRESHOLD = 0.1

# شفافیت لایه‌ی قرمز در تصویر overlay
OVERLAY_ALPHA = 0.4

OVERLAY_FILENAME = "lv_segmentation_overlay.png"
AREA_JSON_FILENAME = "lv_area_cm2.json"


# ==============================================================================
# بارگذاری مدل
# ==============================================================================

def _resolve_device(device: torch.device | str | None) -> torch.device:
    """اگر device داده نشده باشد CUDA (در صورت وجود) وگرنه CPU برمی‌گرداند."""
    if device is None:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device)


def load_lv_model(
    model_path: str | os.PathLike,
    device: torch.device | str | None = None,
) -> torch.nn.Module:
    """
    بارگذاری مدل U-Net++ از فایل checkpoint.

    ورودی:
        model_path: مسیر فایل وزن‌ها (best.pth)
        device: مقصد اجرا؛ اگر None باشد خودکار انتخاب می‌شود

    خروجی:
        مدل PyTorch روی device مشخص‌شده و در حالت eval
    """
    model = smp.UnetPlusPlus(
        encoder_name="timm-efficientnet-b4",
        encoder_weights=None,   # وزن‌ها کامل از checkpoint می‌آیند، نه ImageNet
        in_channels=1,          # ورودی grayscale
        classes=1,              # تک‌کلاسه: فقط LV
    )

    resolved_device = _resolve_device(device)

    # checkpoint ممکن است خودِ state_dict باشد یا زیر کلید "model" ذخیره شده باشد
    checkpoint = torch.load(model_path, map_location=resolved_device)
    state_dict = checkpoint.get("model", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model.load_state_dict(state_dict)

    model.to(resolved_device)
    model.eval()
    return model


# ==============================================================================
# پیش‌پردازش → inference → پس‌پردازش ماسک
# ==============================================================================

def _preprocess_image(image_bgr: np.ndarray) -> torch.Tensor:
    """
    آماده‌سازی تصویر برای مدل: grayscale، resize به ابعاد مدل،
    و نرمال‌سازی به بازه‌ی [-1, 1].

    خروجی:
        تنسور float32 با shape (1, 1, H, W)
    """
    image_gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    image_resized = cv2.resize(image_gray, MODEL_INPUT_SIZE)
    image_normalized = (image_resized.astype(np.float32) / 255.0 - 0.5) / 0.5
    return torch.from_numpy(image_normalized).unsqueeze(0).unsqueeze(0)


def _predict_mask(model: torch.nn.Module, image_bgr: np.ndarray) -> np.ndarray:
    """
    اجرای inference و برگرداندن ماسک باینری (0/1) هم‌اندازه با تصویر ورودی.
    """
    device = next(model.parameters()).device
    input_tensor = _preprocess_image(image_bgr).to(device)

    with torch.no_grad():
        probs = torch.sigmoid(model(input_tensor))

    mask = (probs.cpu().numpy()[0, 0] > PROB_THRESHOLD).astype(np.uint8)

    # برگرداندن ماسک به ابعاد اصلی تصویر
    h, w = image_bgr.shape[:2]
    return cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)


def _postprocess_mask(mask: np.ndarray) -> np.ndarray:
    """
    تمیزکاری ماسک: هموارسازی لبه‌ها، حذف نویز با عملیات مورفولوژیک،
    و نگه‌داشتن فقط بزرگ‌ترین ناحیه‌ی پیوسته (خودِ LV).

    خروجی:
        ماسک uint8 با مقادیر 0/255
    """
    mask = (mask * 255).astype(np.uint8)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # نواحی کوچک جدا از LV (نویز مدل) حذف می‌شوند
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    clean_mask = np.zeros_like(mask)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        cv2.drawContours(clean_mask, [largest], -1, 255, thickness=cv2.FILLED)
    return clean_mask


# ==============================================================================
# ساخت overlay و ذخیره‌سازی خروجی‌ها
# ==============================================================================

def _create_overlay(image_bgr: np.ndarray, mask: np.ndarray, area_cm2: float) -> np.ndarray:
    """
    ساخت تصویر overlay برای نمایش نتیجه: ناحیه‌ی LV با قرمز نیمه‌شفاف،
    کانتور سبز، و متن مساحت در گوشه‌ی تصویر.
    """
    result = image_bgr.copy()

    red_layer = np.zeros_like(image_bgr)
    red_layer[:, :, 2] = 255
    mask_bool = mask > 0
    if np.any(mask_bool):
        blended = cv2.addWeighted(image_bgr, 1 - OVERLAY_ALPHA, red_layer, OVERLAY_ALPHA, 0)
        result[mask_bool] = blended[mask_bool]

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(result, contours, -1, (0, 255, 0), 2)

    text = f"LV Area: {area_cm2:.2f} cm2"
    cv2.putText(result, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    return result


def _save_outputs(
    output_dir: str | os.PathLike,
    overlay: np.ndarray,
    pixels_per_cm: float,
    area_px: int,
    area_cm2: float,
) -> dict[str, str]:
    """ذخیره‌ی تصویر overlay و فایل JSON مساحت؛ مسیر فایل‌ها را برمی‌گرداند."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    overlay_path = out / OVERLAY_FILENAME
    json_path = out / AREA_JSON_FILENAME

    cv2.imwrite(str(overlay_path), overlay)

    payload = {
        "pixels_per_cm": pixels_per_cm,
        "area_px": area_px,
        "area_cm2": area_cm2,
        "view": "a4c/a2c",
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return {
        "overlay_png": str(overlay_path),
        "area_json": str(json_path),
    }


# ==============================================================================
# run_lv_segmentation — نقطه‌ی ورود این ماژول؛ processing.process_video فقط برای a4c/a2c صداش می‌زنه
# ==============================================================================

def run_lv_segmentation(
    image_bgr: np.ndarray,
    pixels_per_cm: float,
    model_path: str | os.PathLike,
    device: torch.device | str | None = None,
    output_dir: str | os.PathLike | None = None,
) -> dict[str, Any]:
    """
    اجرای کامل سگمنتیشن بطن چپ و محاسبه‌ی مساحت آن.

    ورودی:
        image_bgr: فریم اکو (BGR) در نمای A4C یا A2C
        pixels_per_cm: کالیبراسیون مقیاس تصویر
        model_path: مسیر وزن‌های مدل (best.pth)
        device: مقصد اجرای مدل؛ اگر None باشد خودکار انتخاب می‌شود
        output_dir: اگر داده شود، overlay و JSON مساحت آنجا ذخیره می‌شوند

    خروجی:
        {
            "pixels_per_cm": float,
            "area_px": int,          # مساحت LV به پیکسل
            "area_cm2": float,       # مساحت LV به سانتی‌متر مربع
            "saved_paths": dict,     # مسیر فایل‌های ذخیره‌شده (خالی اگر output_dir نباشد)
        }
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")

    # --- مرحله ۱: می‌ره داخل load_lv_model و مدل U-Net++ رو از checkpoint لود می‌کنه (هر بار از صفر) ---
    model = load_lv_model(model_path, device)

    # --- مرحله ۲: پیش‌پردازش تصویر + inference → ماسک خام باینری هم‌اندازه با تصویر ورودی ---
    raw_mask = _predict_mask(model, image_bgr)

    # --- مرحله ۳: تمیزکاری ماسک (حذف نویز، نگه‌داشتن فقط بزرگ‌ترین ناحیه) ---
    clean_mask = _postprocess_mask(raw_mask)

    # --- مرحله ۴: شمارش پیکسل‌های ماسک و تبدیل به cm² با pixel_area_to_cm2 ---
    area_px = int(np.sum(clean_mask > 0))
    area_cm2 = pixel_area_to_cm2(area_px, pixels_per_cm)

    # --- مرحله ۵: ساخت تصویر overlay برای نمایش/دیباگ ---
    overlay = _create_overlay(image_bgr, clean_mask, area_cm2)

    # --- مرحله ۶ (آخر): اگه output_dir داده شده، overlay + JSON مساحت رو ذخیره می‌کنه ---
    saved_paths: dict[str, str] = {}
    if output_dir:
        saved_paths = _save_outputs(output_dir, overlay, pixels_per_cm, area_px, area_cm2)

    return {
        "pixels_per_cm": pixels_per_cm,
        "area_px": area_px,
        "area_cm2": area_cm2,
        "saved_paths": saved_paths,
    }

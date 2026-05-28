"""
Left Ventricle (LV) segmentation and area calculation (cm²).
Uses a deep learning model (UnetPlusPlus) to segment the LV in A4C/A2C views.
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

# اندازه ورودی مدل U-Net++
MODEL_INPUT_SIZE = (256, 256)

# آستانه برای تبدیل probability map به ماسک باینری
THRESHOLD = 0.1


def load_lv_model(model_path: str | os.PathLike, device: torch.device | str | None = None) -> torch.nn.Module:
    """
    بارگذاری مدل U-Net++ با encoder timm-efficientnet-b4.
    
    خروجی:
        مدل PyTorch در حالت eval
    """
    model = smp.UnetPlusPlus(
        encoder_name="timm-efficientnet-b4",
        encoder_weights=None,            # وزن‌های encoder از قبل آموزش ندیده
        in_channels=1,                   # ورودی grayscale
        classes=1,                       # یک کلاس خروجی (LV)
    )

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif isinstance(device, str):
        device = torch.device(device)

    state_dict = torch.load(model_path, map_location=device)
    if "model" in state_dict:
        model.load_state_dict(state_dict["model"])
    else:
        model.load_state_dict(state_dict)

    model.to(device)
    model.eval()
    return model


def preprocess_image(image_bgr: np.ndarray) -> torch.Tensor:
    """
    پیش‌پردازش تصویر برای مدل LV:
      ۱) تبدیل به grayscale
      ۲) تغییر اندازه به ۲۵۶×۲۵۶
      ۳) نرمال‌سازی: (pixel/255 - 0.5) / 0.5  → بازه [-1, 1]
      ۴) افزودن ابعاد batch و channel
    
    خروجی:
        تنسور با shape (1, 1, 256, 256)
    """
    image_gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    image_resized = cv2.resize(image_gray, MODEL_INPUT_SIZE)
    image_normalized = image_resized.astype(np.float32) / 255.0
    image_normalized = (image_normalized - 0.5) / 0.5
    image_tensor = torch.tensor(image_normalized).unsqueeze(0).unsqueeze(0)
    return image_tensor.float()


def postprocess_mask(mask: np.ndarray) -> np.ndarray:
    """
    پس‌پردازش ماسک پیش‌بینی‌شده:
      ۱) آستانه‌گذاری
      ۲) Gaussian blur
      ۳) morphological closing و opening
      ۴) نگه‌داشتن فقط بزرگ‌ترین contour
    """
    mask = (mask * 255).astype(np.uint8)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    clean_mask = np.zeros_like(mask)
    if len(contours) > 0:
        largest = max(contours, key=cv2.contourArea)
        cv2.drawContours(clean_mask, [largest], -1, 255, thickness=cv2.FILLED)
    return clean_mask


def create_overlay(original_image: np.ndarray, mask: np.ndarray, area_cm2: float) -> np.ndarray:
    """
    ساخت تصویر overlay:
      - ناحیه LV با رنگ قرمز نیمه‌شفاف
      - کانتور سبز
      - متن مساحت
    """
    result = original_image.copy()
    overlay = np.zeros_like(original_image)
    overlay[:, :, 2] = 255                          # کانال قرمز

    alpha = 0.4
    mask_bool = mask > 0
    if np.any(mask_bool):
        result[mask_bool] = cv2.addWeighted(original_image, 1 - alpha, overlay, alpha, 0)[mask_bool]

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(result, contours, -1, (0, 255, 0), 2)   # کانتور سبز

    text = f"LV Area: {area_cm2:.2f} cm2"
    cv2.putText(result, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    return result


def run_lv_segmentation(
    image_bgr: np.ndarray,               # تصویر BGR
    pixels_per_cm: float,                # 28.6
    model_path: str | os.PathLike,       # مسیر best.pth
    device: torch.device | str | None = None,
    output_dir: str | os.PathLike | None = None,
) -> dict[str, Any]:
    """
    اجرای سگمنتیشن بطن چپ و محاسبه مساحت.
    
    خروجی (مقادیر واقعی از لاگ):
        {
            "pixels_per_cm": 28.6,
            "area_px": 28340,
            "area_cm2": 34.63983568878674,
            "saved_paths": {
                "overlay_png": "C:\\...\\lv_segmentation_overlay.png",
                "area_json": "C:\\...\\lv_area_cm2.json"
            }
        }
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")

    model = load_lv_model(model_path, device)
    actual_device = next(model.parameters()).device
    input_tensor = preprocess_image(image_bgr).to(actual_device)      # (1, 1, 256, 256)

    with torch.no_grad():
        logits = model(input_tensor)                                   # (1, 1, 256, 256)
        probs = torch.sigmoid(logits)                                  # [0, 1]
        probs_np = probs.cpu().numpy()[0, 0]                          # (256, 256)

    mask_pred = (probs_np > THRESHOLD).astype(np.uint8)               # 0.1

    # تغییر اندازه به ابعاد اصلی تصویر
    h, w = image_bgr.shape[:2]
    mask_pred = cv2.resize(mask_pred, (w, h), interpolation=cv2.INTER_LINEAR)

    clean_mask = postprocess_mask(mask_pred)
    area_px = int(np.sum(clean_mask > 0))                             # 28340
    area_cm2 = pixel_area_to_cm2(area_px, pixels_per_cm)             # 34.639...

    overlay = create_overlay(image_bgr, clean_mask, area_cm2)

    saved_paths = {}
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        overlay_path = out / "lv_segmentation_overlay.png"
        json_path = out / "lv_area_cm2.json"

        cv2.imwrite(str(overlay_path), overlay)

        payload = {
            "pixels_per_cm": pixels_per_cm,
            "area_px": area_px,
            "area_cm2": area_cm2,
            "view": "a4c/a2c"
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        saved_paths["overlay_png"] = str(overlay_path)
        saved_paths["area_json"] = str(json_path)

    return {
        "pixels_per_cm": pixels_per_cm,
        "area_px": area_px,
        "area_cm2": area_cm2,
        "saved_paths": saved_paths,
    }
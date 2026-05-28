"""این فایل کمک‌تابع‌های کوچک سگمنتیشن را برای مرحله اندازه‌گیری فراهم می‌کند."""

from __future__ import annotations

import torch


def segmentation_to_coordinates(
    logits: torch.Tensor,                # (1, 2, 480, 640) — ۲ کانال، هر کدام probability map
    normalize: bool = True,
    order: str = "YX"
) -> torch.Tensor:
    # """
    # تبدیل probability map حاصل از segmentation به مختصات نقاط کلیدی.
    
    # منطق:
    #   - Weighted centroid: هر پیکسل یک وزن (احتمال) دارد.
    #   - مختصات نهایی = میانگین وزنی موقعیت‌ها.
    #   - مشابه مرکز جرم در فیزیک.
    
    # ریاضی:
    #   x_center = sum(x * p) / sum(p)
    #   y_center = sum(y * p) / sum(p)
    
    # ورودی:
    #     logits   : تنسور با shape (..., n_points, H, W)
    #                (بعد از sigmoid، مقادیر بین ۰ و ۱)
    #     normalize: اگر True، مختصات در بازه [0,1] نرمال‌سازی می‌شوند
    #                (برای process_video: normalize=False)
    #     order    : ترتیب خروجی:
    #                "YX" → [y, x]
    #                "XY" → [x, y]
    #                (برای process_video: order="XY")
    
    # خروجی:
    #     تنسور با shape (..., n_points, 2)
    #     مثلاً: shape (1, 2, 2) = [[[158, 266], [299, 268]]]
    
    # مثال با لاگ واقعی:
    #     ورودی: logits با shape (1, 2, 480, 640)
    #     خروجی: tensor([[[158.2, 266.1], [299.3, 268.4]]])
    # """
    # ساخت ماتریس‌های مختصات سطری و ستونی
    predictions_rows, predictions_cols = torch.meshgrid(
        torch.arange(logits.shape[-2], device=logits.device),   # [0, 1, 2, ..., 479]  (H)
        torch.arange(logits.shape[-1], device=logits.device),   # [0, 1, 2, ..., 639]  (W)
        indexing="ij",
    )
    # predictions_rows.shape = (480, 640)  — هر درایه = شماره سطر
    # predictions_cols.shape = (480, 640)  — هر درایه = شماره ستون

    # محاسبه weighted sum
    predictions_rows = predictions_rows * logits                # y_weighted
    predictions_cols = predictions_cols * logits                # x_weighted

    # جمع در راستای H و W → centroid
    predictions_rows = predictions_rows.sum(dim=(-2, -1)) / (logits.sum(dim=(-2, -1)) + 1e-8)
    # predictions_rows: میانگین وزنی Y
    predictions_cols = predictions_cols.sum(dim=(-2, -1)) / (logits.sum(dim=(-2, -1)) + 1e-8)
    # predictions_cols: میانگین وزنی X

    # نرمال‌سازی (اختیاری)
    if normalize:
        predictions_rows = predictions_rows / logits.shape[-2]  # تقسیم بر H
        predictions_cols = predictions_cols / logits.shape[-1]  # تقسیم بر W

    # انتخاب ترتیب خروجی
    if order == "YX":
        return torch.stack([predictions_rows, predictions_cols], dim=-1)
        # shape: (..., 2) → [y, x]
    if order == "XY":
        return torch.stack([predictions_cols, predictions_rows], dim=-1)
        # shape: (..., 2) → [x, y]
        # در process_video از این استفاده می‌شود

    raise ValueError(f"Invalid order: {order}")
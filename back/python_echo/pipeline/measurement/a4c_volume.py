"""
Apical four-chamber style atrial area segmentation (pixel + cm²).

Used by `main.py` when the detected view is `a4c`. Requires a B-mode crop (BGR)
and `pixels_per_cm` on that image (same calibration as linear measurements).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from pipeline.measurement.scale import pixel_area_to_cm2


def _fit_and_clip_ellipse(
    mask: np.ndarray,
    valve_a: tuple[int, int],
    valve_b: tuple[int, int],
    clip_x: int,
    keep_left: bool,
) -> np.ndarray:
    """
    Ellipse fit + bresh MOVAZI ba khat abi (partow valve):

      1. Ellipse ro fit mikone
      2. Gap bala-ye ellipse ra ta khat abi por mikone (naghie sabz ham hesab beshe)
      3. Bresh az rooye khat abi KAJ (valve_a -> valve_b), na khat afoghi saaf
         => labe-ye bala movazi ba khat abi mishe
      4. clip_x: khat amodi - do atrium az ham joda mishe
         keep_left=True  -> left atrium  (rast hazf)
         keep_left=False -> right atrium (chap hazf)

    Age kontor kam-e (<5 point) mask asli ro barmigardone.
    """
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return mask
    cnt = max(cnts, key=cv2.contourArea)
    if len(cnt) < 5:
        return mask

    result = np.zeros_like(mask)
    cv2.ellipse(result, cv2.fitEllipse(cnt), 1, -1)

    h, w = result.shape
    ys, xs = np.mgrid[0:h, 0:w]

    # Khat abi kaj: cross product alamat-e samt-e har pixel ro midhe
    dx, dy = valve_b[0] - valve_a[0], valve_b[1] - valve_a[1]
    side = dx * (ys - valve_a[1]) - dy * (xs - valve_a[0])
    # samt-e atrium = samti ke ellipse center toosh-e (paeen-e khat)
    cy_e, cx_e = np.argwhere(result > 0).mean(axis=0)
    ref_side = dx * (cy_e - valve_a[1]) - dy * (cx_e - valve_a[0])
    below_line = (np.sign(side) == np.sign(ref_side))    # paeen-e khat abi kaj

    # Gap por kardan: har soton ke ellipse dare, az khat abi ta ellipse ro por kon
    has_px = np.any(result > 0, axis=0)
    cum    = np.cumsum(result, axis=0)
    gap    = (cum == 0) & has_px & below_line            # faze khali bala-ye ellipse (paeen-e khat)
    result = np.maximum(result, gap.astype(np.uint8))

    result[~below_line] = 0      # bala-ye khat abi kaj hazf
    if keep_left:
        result[:, clip_x:] = 0   # left atrium: rast hazf
    else:
        result[:, :clip_x] = 0   # right atrium: chap hazf
    return result


def _get_seeds(
    best_center: tuple[int, int],
    best_rays: list[tuple[int, int]],
    gray_img: np.ndarray,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Seed point baraye left/right atrium peida mikone.
    Atrium por az khoon = tira -> tarin pixel ro dar yek radius 20px peida mikone.
    Taghmini: left seed = miangine markaz + ray-chap + ray-paeen.
    """
    cx, cy = best_center
    e_r, e_d, e_l, _ = best_rays

    guess_l = (int((cx + e_l[0] + e_d[0]) / 3), int((cy + e_l[1] + e_d[1]) / 3))
    guess_r = (int((cx + e_r[0] + e_d[0]) / 3), int((cy + e_r[1] + e_d[1]) / 3))

    def darkest_near(x: int, y: int, radius: int = 20) -> tuple[int, int]:
        hh, ww = gray_img.shape
        y0, y1 = max(0, y - radius), min(hh, y + radius + 1)
        x0, x1 = max(0, x - radius), min(ww, x + radius + 1)
        patch = gray_img[y0:y1, x0:x1]
        dy, dx = np.unravel_index(np.argmin(patch), patch.shape)
        return (x0 + int(dx), y0 + int(dy))

    return darkest_near(*guess_l), darkest_near(*guess_r)


def _flood_fill_chamber(seed: tuple[int, int], boundary_mask: np.ndarray) -> np.ndarray | None:
    """
    Az seed shoru mikone va tamam pixel-haye mottasel (value=0) ro ba 128 por mikone.
    Divara (255) jologiresh ro migirand.
    Agar chizi por nashod None bar migardone.
    """
    flood = boundary_mask.copy()
    h, w = flood.shape
    cv2.floodFill(flood, np.zeros((h + 2, w + 2), np.uint8), seed, 128)
    chamber = (flood == 128).astype(np.uint8)
    return chamber if cv2.countNonZero(chamber) > 0 else None


def run_a4c_atrial_areas(
    image_bgr: np.ndarray,
    pixels_per_cm: float,
    *,
    exclusion_radius: int = 70,
    output_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """
    Masahat left/right atrium ra dar nama A4C hesab mikone.

    Marahel:
      1. Markaz + 4 partow behine (ravshan tarin masir)
      2. Threshold + morphological open -> pixel haye divar
      3. Bridge zadan gap ha ta divara closed beshand
      4. Morphological close + keshidan partow ha rooye mask
      5. Flood fill har atrium az seed
      6. Ellipse fit + bresh az bala (valve plane) -> shekl nahaii
      7. Hesab masahat pixel va cm2
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive.")

    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # blur bala baraye partow ha - khat ha ravshan tar mishand
    blur_rays = cv2.GaussianBlur(gray, (15, 15), 0)

    # ---- Partow ha: markaz behine peida mikonim ----
    # partow be samte ravshan tarin masir miره - divar haye qalb (sefid) ro dokhtar mikone
    def best_ray(cx: int, cy: int, angles: range, length: int) -> tuple[float, tuple[int, int]]:
        maxv, best_end = -1.0, (cx, cy)
        for a in angles:
            rad = math.radians(a)
            dx, dy = length * math.cos(rad), length * math.sin(rad)
            xs = np.linspace(cx, cx + dx, int(length)).astype(int)
            ys = np.linspace(cy, cy + dy, int(length)).astype(int)
            valid = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
            if not np.any(valid):
                continue
            val = float(np.mean(blur_rays[ys[valid], xs[valid]]))
            if val > maxv:
                maxv = val
                best_end = (int(cx + dx), int(cy + dy))
        return maxv, best_end

    ray_len = int(h * 0.33)   # taghribn yek sevom ertefa - partow dakhel ghazf mimone
    best_center = (w // 2, h // 2)
    best_score  = -1.0
    best_rays: list[tuple[int, int]] = []

    # grid search dar 40-70% ertefa va 40-60% arz
    for cy in range(int(h * 0.4), int(h * 0.7), 5):
        for cx in range(int(w * 0.4), int(w * 0.6), 5):
            s_r, e_r = best_ray(cx, cy, range(-30,  31, 2), ray_len)   # rast
            s_d, e_d = best_ray(cx, cy, range( 60, 121, 2), ray_len)   # paeen
            s_l, e_l = best_ray(cx, cy, range(150, 211, 2), ray_len)   # chap
            s_u, e_u = best_ray(cx, cy, range(240, 301, 2), ray_len)   # bala
            tot = s_r + s_d + s_l + s_u
            if tot > best_score:
                best_score = tot
                best_center = (cx, cy)
                best_rays   = [e_r, e_d, e_l, e_u]

    # ---- Divar ha: threshold + morphological open ----
    # threshold 75 divar haye echo (sefid) ro az khon (tira) joda mikone
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blur, 75, 255, cv2.THRESH_BINARY)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open)

    # ---- Endpoint ha + bridge zadan gap ha ----
    # kontor haye bozorg ro peida mikonim va 4 noghte-ye extreme har kontor ro bar midarim
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    endpoints: list[tuple[int, int]] = []
    for cnt in contours:
        if cv2.contourArea(cnt) > 200:
            endpoints.extend([
                tuple(cnt[cnt[:, :, 0].argmin()][0]),  # chasb-tarin chap
                tuple(cnt[cnt[:, :, 0].argmax()][0]),  # chasb-tarin rast
                tuple(cnt[cnt[:, :, 1].argmin()][0]),  # chasb-tarin bala
                tuple(cnt[cnt[:, :, 1].argmax()][0]),  # chasb-tarin paeen
            ])

    bridged = cleaned.copy()
    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            pt1, pt2 = endpoints[i], endpoints[j]
            mid = ((pt1[0] + pt2[0]) // 2, (pt1[1] + pt2[1]) // 2)
            # nazdik be markaz = valve plane -> bridge nemizanim (ghaleb nadarad)
            if any(
                math.hypot(p[0] - best_center[0], p[1] - best_center[1]) < exclusion_radius
                for p in (pt1, pt2, mid)
            ):
                continue
            d = math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
            if 20 < d < 80:
                cv2.line(bridged, pt1, pt2, 255, 3)

    # ---- Close + partow ha rooye mask ----
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(bridged, cv2.MORPH_CLOSE, kernel_close)
    for ep in best_rays:
        cv2.line(closed, best_center, ep, 255, 3)  # partow ha divare bein atrium va ventricle mishe

    # ---- Flood fill ----
    left_seed, right_seed = _get_seeds(best_center, best_rays, blur_rays)
    raw_l = _flood_fill_chamber(left_seed,  closed)
    raw_r = _flood_fill_chamber(right_seed, closed)

    # ---- Ellipse fit + bresh movazi ba khat abi ----
    # best_rays = [e_r, e_d, e_l, e_u]  (rast, paeen, chap, bala)
    # khat abi valve: left atrium ba partow chap, right atrium ba partow rast bresh mikhore
    # clip_x = khat amodi separator (best_center[0]) -> do atrium az ham joda mishe
    e_r, _e_d, e_l, _e_u = best_rays
    clip_x = best_center[0]
    mask_l = _fit_and_clip_ellipse(raw_l, best_center, e_l, clip_x, keep_left=True)  if raw_l is not None else None
    mask_r = _fit_and_clip_ellipse(raw_r, best_center, e_r, clip_x, keep_left=False) if raw_r is not None else None

    # ---- Masahat ----
    areas_px: dict[str, int] = {}
    if mask_r is not None:
        areas_px["right_atrium"] = int(np.sum(mask_r))
    if mask_l is not None:
        areas_px["left_atrium"] = int(np.sum(mask_l))

    scale     = float(pixels_per_cm)
    areas_cm2 = {k: pixel_area_to_cm2(px, scale) for k, px in areas_px.items()}

    # ---- Overlay ----
    overlay = image_bgr.copy()

    # divar ha ra kam rooshan mikone
    overlay[closed == 255] = (0.85 * overlay[closed == 255] + 0.15 * 255).astype(np.uint8)

    for ep in best_rays:
        cv2.line(overlay, best_center, ep, (255, 200, 0), 2)

    def draw_chamber(mask: np.ndarray | None, color: tuple, name: str) -> None:
        if mask is None:
            return
        overlay[mask == 1] = (0.6 * overlay[mask == 1] + 0.4 * np.array(color)).astype(np.uint8)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, cnts, -1, (0, 0, 255), 1)
        m = cv2.moments(mask)
        if m["m00"] != 0:
            cv2.putText(
                overlay, f"{areas_cm2.get(name, 0.0):.1f} cm2",
                (int(m["m10"] / m["m00"]) - 30, int(m["m01"] / m["m00"]) + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA,
            )

    draw_chamber(mask_r, (0,   0, 200), "right_atrium")   # abi
    draw_chamber(mask_l, (200, 0,   0), "left_atrium")    # ghermez tire

    cv2.circle(overlay, right_seed, 4, (0, 255, 0), -1)
    cv2.circle(overlay, left_seed,  4, (0, 255, 0), -1)

    # exclusion circle (valve plane area) - nime shafaf
    circle_ov = overlay.copy()
    cv2.circle(circle_ov, best_center, exclusion_radius, (255, 255, 255), 1)
    cv2.addWeighted(circle_ov, 0.3, overlay, 0.7, 0, overlay)

    # ---- Zakhire ----
    saved_paths: dict[str, str] = {}
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        overlay_path = out / "a4c_atrial_overlay.png"
        json_path    = out / "a4c_area_cm2.json"
        cv2.imwrite(str(overlay_path), overlay)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump({"pixels_per_cm": scale, "areas_cm2": areas_cm2, "areas_px": areas_px}, f, indent=2)
        saved_paths["overlay_png"] = str(overlay_path)
        saved_paths["areas_json"]  = str(json_path)

    return {
        "pixels_per_cm": scale,
        "best_center":   {"x": int(best_center[0]), "y": int(best_center[1])},
        "areas_px":      areas_px,
        "areas_cm2":     areas_cm2,
        "saved_paths":   saved_paths,
    }

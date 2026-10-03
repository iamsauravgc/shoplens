from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

HEATMAP_SEGMENTS = ("full", "morning", "afternoon", "evening")


def _add_gaussian_blob(heat: np.ndarray, cx: float, cy: float, sigma: float) -> None:
    h, w = heat.shape
    radius = int(sigma * 3)
    x0, x1 = max(int(cx) - radius, 0), min(int(cx) + radius + 1, w)
    y0, y1 = max(int(cy) - radius, 0), min(int(cy) + radius + 1, h)
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    heat[y0:y1, x0:x1] += np.exp(-(((xs - cx) ** 2 + (ys - cy) ** 2) / (2 * sigma**2)))


def generate_heatmap(frame_shape: tuple[int, ...], positions, sigma: float = 25.0) -> np.ndarray:
    heat = np.zeros(frame_shape[:2], dtype=np.float32)
    for cx, cy in positions:
        _add_gaussian_blob(heat, cx, cy, sigma)
    if heat.max() > 0:
        heat /= heat.max()
    return heat


def aggregate_heatmaps(heats: list[np.ndarray]) -> np.ndarray:
    total = np.sum(heats, axis=0) if heats else None
    if total is None or total.max() == 0:
        return np.zeros((1, 1), dtype=np.float32)
    return (total / total.max()).astype(np.float32)


def overlay_heatmap(frame_bgr: np.ndarray, heat: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    heat_resized = cv2.resize(heat, (frame_bgr.shape[1], frame_bgr.shape[0]))
    colored = cv2.applyColorMap((np.clip(heat_resized, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.addWeighted(colored, alpha, frame_bgr, 1 - alpha, 0)


def export_png(image_bgr: np.ndarray, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image_bgr)
    return path


# distinct from the JET colormap so outlines stay readable on hot areas
ZONE_COLORS = [(255, 0, 255), (255, 128, 0), (0, 255, 128), (255, 255, 0), (128, 0, 255), (0, 255, 255)]


def overlay_zones(image_bgr: np.ndarray, zones) -> np.ndarray:
    for i, zone in enumerate(zones):
        pts = np.array([(int(p[0]), int(p[1])) for p in zone.polygon], dtype=np.int32)
        if len(pts) < 3:
            continue
        color = ZONE_COLORS[i % len(ZONE_COLORS)]
        fill = image_bgr.copy()
        cv2.fillPoly(fill, [pts], color)
        cv2.addWeighted(fill, 0.15, image_bgr, 0.85, 0, image_bgr)
        cv2.polylines(image_bgr, [pts], True, color, 2, cv2.LINE_AA)
        x, y = int(pts[:, 0].min()), int(pts[:, 1].min())
        (tw, th), _ = cv2.getTextSize(zone.name, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        x = min(x, image_bgr.shape[1] - tw - 8)  # keep the label inside the frame
        y = min(y, image_bgr.shape[0] - th - 8)
        x, y = max(x, 0), max(y, 0)
        cv2.rectangle(image_bgr, (x, y), (x + tw + 6, y + th + 8), (0, 0, 0), -1)
        cv2.putText(
            image_bgr, zone.name, (x + 3, y + th + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA
        )
    return image_bgr


def split_positions_by_segment(
    positions_with_frames: list[tuple[int, tuple[float, float]]],
) -> dict[str, list[tuple[float, float]]]:
    """Clip-relative thirds map to morning/afternoon/evening.

    CCTV footage has no wall-clock time, so each segment is a third of the clip's
    frame span. Documented as a design decision in README.
    """
    out: dict[str, list[tuple[float, float]]] = {s: [] for s in HEATMAP_SEGMENTS}
    if not positions_with_frames:
        return out
    frames = [f for f, _ in positions_with_frames]
    lo, hi = min(frames), max(frames)
    span = max(hi - lo, 1)
    for frame_idx, pos in positions_with_frames:
        out["full"].append(pos)
        t = (frame_idx - lo) / span
        if t < 1 / 3:
            out["morning"].append(pos)
        elif t < 2 / 3:
            out["afternoon"].append(pos)
        else:
            out["evening"].append(pos)
    return out


def heatmap_response_path(job_id: str, segment: str) -> str:
    return f"heatmaps/{job_id}/{segment}.png"

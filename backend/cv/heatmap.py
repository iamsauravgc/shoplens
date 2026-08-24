from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

TIME_SEGMENTS = {
    "morning": (9, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
}


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


def segment_key_for_timestamp(timestamp_hour: float) -> str:
    # TODO(epic-4 day 3): Mall Dataset has no wall-clock time — decide the mapping used for
    # time-segmented heatmaps (e.g. split video duration into thirds) and document it
    for name, (lo, hi) in TIME_SEGMENTS.items():
        if lo <= timestamp_hour < hi:
            return name
    return "full"


def heatmap_response_path(job_id: str, segment: str) -> str:
    return f"heatmaps/{job_id}/{segment}.png"

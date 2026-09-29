"""Epic 4 verification: aggregate heatmaps over all 2000 Mall Dataset frames + time segments.

Run:  .venv/Scripts/python scripts/build_mall_heatmaps.py   (from backend/)
Outputs: data/out/heatmaps/mall_{full,morning,afternoon,evening}.png
Caches per-frame person centroids in data/mall_positions.json (reused by later runs).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import cv2

from app.config import get_settings
from cv.detector import BEST_CONF, detect_persons
from cv.heatmap import export_png, generate_heatmap, overlay_heatmap, split_positions_by_segment


def detect_all_positions() -> list[tuple[int, tuple[float, float]]]:
    data_dir = get_settings().data_dir
    cache = data_dir / "mall_positions.json"
    if cache.exists():
        raw = json.loads(cache.read_text())
        print(f"loaded {len(raw)} cached positions from {cache.name}")
        return [(int(f), (float(x), float(y))) for f, x, y in raw]

    frames_dir = data_dir / "mall_dataset" / "frames"
    paths = sorted(frames_dir.glob("*.jpg"))
    print(f"detecting persons on {len(paths)} frames (first run only, ~5-10 min)...")

    positions: list[tuple[int, tuple[float, float]]] = []
    t0 = time.time()
    for i, p in enumerate(paths):
        img = cv2.imread(str(p))
        if img is None:
            continue
        boxes = detect_persons(img, conf=BEST_CONF)
        for x1, y1, x2, y2 in boxes:
            positions.append((i + 1, ((float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2)))
        if (i + 1) % 200 == 0:
            rate = (i + 1) / (time.time() - t0)
            print(f"  {i + 1}/{len(paths)} frames, {len(positions)} positions, "
                  f"{rate:.1f} fps, ETA {(len(paths) - i - 1) / max(rate, 0.1) / 60:.1f} min")

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([[f, round(x, 2), round(y, 2)] for f, (x, y) in positions]))
    print(f"done in {time.time() - t0:.0f}s, cached -> {cache}")
    return positions


def main() -> int:
    data_dir = get_settings().data_dir
    out_dir = data_dir / "out" / "heatmaps"

    positions = detect_all_positions()
    segments = split_positions_by_segment(positions)

    first_frame = cv2.imread(str(sorted((data_dir / "mall_dataset" / "frames").glob("*.jpg"))[0]))

    for segment, pts in segments.items():
        if not pts:
            print(f"{segment}: no positions, skipped")
            continue
        heat = generate_heatmap(first_frame.shape, pts)
        overlay = overlay_heatmap(first_frame, heat)
        path = export_png(overlay, out_dir / f"mall_{segment}.png")
        print(f"{segment:>10}: {len(pts):>7} positions -> {path}")

    print(f"\nEpic 4 DoD 1-2: exported {sum(1 for p in segments.values() if p)} heatmap PNGs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

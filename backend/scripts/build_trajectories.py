"""Regenerate data/trajectories.json locally (Epic 2 output) — every 5th mall frame, full clip.

Run:  .venv/Scripts/python scripts/build_trajectories.py   (from backend/)
Format matches notebooks/tracking.ipynb: {"meta": {...}, "trajectories": {id: [{frame,cx,cy}]}}
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent

import cv2

from app.config import get_settings
from cv.detector import BEST_CONF, detect_persons
from cv.tracker import BEST_MAX_AGE, BEST_N_INIT, build_trajectories, make_tracker, update_tracks

FRAME_STEP = 5


def main() -> int:
    out_path = REPO_ROOT / "data" / "trajectories.json"
    frames_dir = get_settings().data_dir / "mall_dataset" / "frames"
    paths = sorted(frames_dir.glob("*.jpg"))

    tracker = make_tracker(max_age=BEST_MAX_AGE, n_init=BEST_N_INIT)
    frame_data: dict[int, list] = {}
    t0 = time.time()
    sampled = 0
    for i, p in enumerate(paths):
        if i % FRAME_STEP != 0:
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        boxes = detect_persons(img, conf=BEST_CONF)
        scores = [BEST_CONF] * len(boxes)
        frame_data[i] = update_tracks(tracker, boxes, scores, img)
        sampled += 1
        if sampled % 100 == 0:
            rate = sampled / (time.time() - t0)
            print(f"  {sampled} sampled frames, {len(frame_data)} tracked, {rate:.1f} fps, "
                  f"ETA {(len(paths) // FRAME_STEP - sampled) / max(rate, 0.1) / 60:.1f} min", flush=True)

    trajectories, _ = build_trajectories(frame_data)
    payload = {
        "meta": {
            "frames": len(frame_data),
            "unique_track_ids": len(trajectories),
            "best_max_age": BEST_MAX_AGE,
            "best_n_init": BEST_N_INIT,
            "conf_threshold": BEST_CONF,
            "frame_step": FRAME_STEP,
            "source": "regenerated locally from mall frames",
        },
        "trajectories": {
            str(tid): [{"frame": int(pt["frame"]), "cx": pt["cx"], "cy": pt["cy"]} for pt in pts]
            for tid, pts in trajectories.items()
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload))
    print(f"done in {time.time() - t0:.0f}s -> {out_path} ({len(trajectories)} tracks, "
          f"{sum(len(v) for v in trajectories.values())} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

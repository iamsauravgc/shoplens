"""Epic 3 verification: zone persistence round-trip + intersection logic on 100 mall frames.

Run:  .venv/Scripts/python scripts/verify_zones_100.py   (from backend/)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import cv2

from app.config import get_settings
from app.db import create_zone, delete_zone, fetch_zones
from cv.detector import BEST_CONF, detect_persons
from cv.tracker import build_trajectories, make_tracker, update_tracks
from cv.zones import Zone, assign_zone, compute_zone_visits, peak_hour_per_zone, summarize_zones

FRAME_STEP = 5          # sample every 5th frame -> 100 frames from the first 500
FRAMES_TO_TAKE = 100
MALL_FPS = 30.0         # frame indices are source frames -> one frame = 1/30s
FRAME_INTERVAL_SEC = 1.0 / MALL_FPS

DEMO_ZONES = [
    Zone("demo-entry", "Entrance strip", [(0, 340), (640, 340), (640, 480), (0, 480)]),
    Zone("demo-aisle", "Center aisle", [(200, 100), (440, 100), (440, 340), (200, 340)]),
    Zone("demo-top", "Upper walkway", [(0, 0), (640, 0), (640, 100), (0, 100)]),
]


def verify_zone_persistence() -> bool:
    print("--- zone persistence (SQLite round-trip) ---")
    zone = create_zone("__verify_tmp__", [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}])
    loaded = fetch_zones()
    found = any(z["id"] == zone["id"] and z["name"] == "__verify_tmp__" for z in loaded)
    polygon_ok = found and loaded[[z["id"] for z in loaded].index(zone["id"])]["polygon"][0] == {"x": 1, "y": 2}
    deleted = delete_zone(zone["id"])
    gone = not any(z["id"] == zone["id"] for z in fetch_zones())
    ok = bool(found and polygon_ok and deleted and gone)
    print(f"  create={found} polygon_reloaded={polygon_ok} delete={deleted} gone={gone} -> {'PASS' if ok else 'FAIL'}")
    return ok


def load_frames():
    frames_dir = get_settings().data_dir / "mall_dataset" / "frames"
    paths = sorted(frames_dir.glob("*.jpg"))[: FRAMES_TO_TAKE * FRAME_STEP]
    frames = []
    for i, p in enumerate(paths):
        if i % FRAME_STEP == 0:
            img = cv2.imread(str(p))
            if img is None:
                raise RuntimeError(f"unreadable frame: {p}")
            frames.append((i, img))
    return frames[:FRAMES_TO_TAKE]


def verify_intersection() -> bool:
    print(f"--- intersection on {FRAMES_TO_TAKE} frames (every {FRAME_STEP}th) ---")
    t0 = time.time()

    frames = load_frames()
    tracker = make_tracker()
    frame_data: dict[int, list] = {}
    for idx, frame in frames:
        boxes = detect_persons(frame, conf=BEST_CONF)
        scores = [BEST_CONF] * len(boxes)
        frame_data[idx] = update_tracks(tracker, boxes, scores, frame)
    trajectories, _ = build_trajectories(frame_data)

    db_zones = fetch_zones()
    if db_zones:
        zones = [
            Zone(zone_id=str(z["id"]), name=z["name"],
                 polygon=[(float(p["x"]), float(p["y"])) for p in z["polygon"]])
            for z in db_zones
        ]
        print(f"  using {len(zones)} zone(s) from the database")
    else:
        zones = DEMO_ZONES
        print("  no zones in database — using demo zones for the logic check")

    visits = compute_zone_visits(trajectories, zones, FRAME_INTERVAL_SEC)
    summary = summarize_zones(visits, zones)
    peak = peak_hour_per_zone(visits, "2026-09-29T09:00:00", fps=MALL_FPS)

    print(f"  processed {len(frames)} frames, {len(trajectories)} tracks, "
          f"{len(visits)} zone visits in {time.time() - t0:.1f}s")
    print(f"  {'zone':<20} {'visitors':>8} {'visits':>7} {'avg_dwell':>10} {'peak_hour':>10}")
    for zone in zones:
        s = summary.get(zone.zone_id, {"unique_visitors": 0, "total_visits": 0, "avg_dwell_seconds": 0})
        print(f"  {zone.name:<20} {s['unique_visitors']:>8} {s['total_visits']:>7} "
              f"{s['avg_dwell_seconds']:>10} {str(peak.get(zone.zone_id, '-')):>10}")

    print("  sample per-frame zone assignments:")
    for idx in [f[0] for f in frames[:5]]:
        persons = frame_data.get(idx, [])
        counts: dict[str, int] = {}
        for p in persons:
            zid = assign_zone(p["centroid"], zones)
            key = next((z.name for z in zones if z.zone_id == zid), "outside")
            counts[key] = counts.get(key, 0) + 1
        print(f"    frame {idx:>4}: {len(persons)} persons -> {counts}")

    ok = len(trajectories) > 0 and len(visits) > 0
    print(f"  tracks>0 and visits>0 -> {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> int:
    persisted = verify_zone_persistence()
    intersected = verify_intersection()
    print(f"\nEpic 3 verification: {'PASS' if persisted and intersected else 'FAIL'}")
    return 0 if persisted and intersected else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.db import fetch_zones
from cv.anomaly import features_from_visits, score_trajectories, zone_index_map
from cv.zones import Zone, compute_zone_visits

FRAME_INTERVAL_SEC = 1 / 30
SEED = 42
SPLIT = 0.8
SHEET_ROWS = 5
SHEET_COLS = 9


def main() -> int:
    labels_dir = REPO_ROOT / "data" / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    raw = json.loads((REPO_ROOT / "data" / "trajectories.json").read_text())
    trajectories = raw.get("trajectories", raw)
    zones = [
        Zone(str(r["id"]), r["name"], [(float(p["x"]), float(p["y"])) for p in r["polygon"]])
        for r in fetch_zones()
    ]
    visits = compute_zone_visits(trajectories, zones, FRAME_INTERVAL_SEC)
    zone_index = zone_index_map(zones)
    features = features_from_visits(visits, trajectories, zones, zone_index)
    scores = score_trajectories(features)

    # same split as training: score only rows the model never saw
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(len(features))
    test_rows = set(int(i) for i in perm[int(SPLIT * len(perm)) :])

    name_of = {z.zone_id: z.name for z in zones}
    rows = []
    for i, (v, feat, score) in enumerate(zip(visits, features, scores)):
        if i not in test_rows:
            continue
        rows.append(
            {
                "row_index": i,
                "track_id": v.track_id,
                "zone": name_of.get(v.zone_id, "?"),
                "entry_frame": v.entry_frame,
                "dwell_seconds": round(float(feat[1]), 2),
                "mean_velocity": round(float(feat[2]), 2),
                "turn_rate": round(float(feat[3]), 3),
                "reconstruction_error": score["error"],
                "flagged": int(score["is_anomaly"]),
                "label": "",
            }
        )

    csv_path = labels_dir / "samples.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    flagged = sum(r["flagged"] for r in rows)
    per_sheet = SHEET_ROWS * SHEET_COLS
    for sheet_idx in range(0, len(rows), per_sheet):
        chunk = rows[sheet_idx : sheet_idx + per_sheet]
        n_cols = min(SHEET_COLS, len(chunk))
        n_rows = int(np.ceil(len(chunk) / n_cols))
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(2.6 * n_cols, 2.6 * n_rows), squeeze=False)
        for ax in axes.flat:
            ax.axis("off")
        for ax, r in zip(axes.flat, chunk):
            visit = visits[r["row_index"]]
            points = [
                p for p in trajectories.get(str(visit.track_id), [])
                if visit.entry_frame <= int(p["frame"]) <= visit.exit_frame
            ]
            xs = [p["cx"] for p in points]
            ys = [p["cy"] for p in points]
            zone = next((z for z in zones if z.name == r["zone"]), None)
            if zone:
                zx = [p[0] for p in zone.polygon] + [zone.polygon[0][0]]
                zy = [p[1] for p in zone.polygon] + [zone.polygon[0][1]]
                ax.plot(zx, zy, color="gray", linewidth=1, linestyle="--")
            ax.plot(xs, ys, color="#f87171" if r["flagged"] else "#38bdf8", linewidth=1.5)
            if xs:
                ax.plot(xs[0], ys[0], "g^", ms=5)
                ax.plot(xs[-1], ys[-1], "ks", ms=4)
            flag = "FLAG" if r["flagged"] else "-"
            ax.set_title(
                f"#{r['row_index']} {flag}\nd={r['dwell_seconds']}s v={r['mean_velocity']}",
                fontsize=8,
                color="#f87171" if r["flagged"] else "#e2e8f0",
            )
            ax.invert_yaxis()
            ax.set_xticks([])
            ax.set_yticks([])
        fig.tight_layout()
        out = labels_dir / f"worksheet_{sheet_idx // per_sheet + 1}.png"
        fig.savefig(out, dpi=90)
        plt.close(fig)
        print(f"wrote {out}")

    print(
        f"\ntest-set visits: {len(rows)} (flagged by model: {flagged})\n"
        f"label file: {csv_path}\n"
        f"Open the worksheet PNGs, look at each numbered path, set label=1 if the movement is\n"
        f"genuinely unusual for a shopper (loitering/erratic), 0 if normal. Then run score_labels.py.\n"
        f"Legend: green triangle = path start, black square = end, dashed gray = zone outline."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

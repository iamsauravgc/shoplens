from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FRAME = REPO_ROOT / "data" / "mall_dataset" / "frames" / "seq_000001.jpg"
TRAJECTORIES = REPO_ROOT / "data" / "trajectories.json"
LABELS = REPO_ROOT / "data" / "labels" / "samples.csv"
OUT = REPO_ROOT / "docs" / "evidence" / "anomaly_trajectories.png"

CO_NORMAL = "#1b4bf1"
CO_ANOMALY = "#e5484d"
CO_UNLABELED = "#b6bcc7"


def load_labels() -> tuple[set[str], set[str]]:
    positive: set[str] = set()
    negative: set[str] = set()
    with LABELS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = row["track_id"].strip()
            if row["label"].strip() in {"1", "true", "yes"}:
                positive.add(tid)
            else:
                negative.add(tid)
    # a track labeled both ways counts as anomalous (it contains an anomalous visit)
    return positive, negative - positive


def main() -> int:
    trajectories = json.loads(TRAJECTORIES.read_text(encoding="utf-8"))["trajectories"]
    anomalous, normal = load_labels()
    unlabeled = set(trajectories) - anomalous - normal

    img = cv2.cvtColor(cv2.imread(str(FRAME)), cv2.COLOR_BGR2RGB)
    fig, ax = plt.subplots(figsize=(11, 8.25), dpi=150)
    ax.imshow(img, extent=(0, img.shape[1], img.shape[0], 0))

    def draw(track_ids: set[str], color: str, width: float, alpha: float, z: int) -> None:
        for tid in track_ids:
            pts = trajectories.get(tid)
            if not pts:
                continue
            ax.plot(
                [p["cx"] for p in pts],
                [p["cy"] for p in pts],
                color=color,
                linewidth=width,
                alpha=alpha,
                zorder=z,
                solid_capstyle="round",
            )

    draw(unlabeled, CO_UNLABELED, 0.6, 0.12, 1)
    draw(normal, CO_NORMAL, 1.8, 0.8, 2)
    draw(anomalous, CO_ANOMALY, 3.2, 0.95, 3)

    ax.set_xlim(0, img.shape[1])
    ax.set_ylim(img.shape[0], 0)
    ax.set_axis_off()
    ax.set_title(
        "Normal vs anomalous trajectories — Mall Dataset frame",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    handles = [
        plt.Line2D([], [], color=CO_ANOMALY, lw=3.2, label=f"Anomalous ({len(anomalous)} tracks)"),
        plt.Line2D([], [], color=CO_NORMAL, lw=1.8, alpha=0.8, label=f"Normal ({len(normal)} tracks)"),
        plt.Line2D([], [], color=CO_UNLABELED, lw=0.6, alpha=0.12, label=f"Unlabeled context ({len(unlabeled)} tracks)"),
    ]
    ax.legend(handles=handles, loc="lower right", framealpha=0.9, fontsize=9)
    fig.text(
        0.5,
        0.015,
        "Track-level view: a track is anomalous if any of its labeled visits is anomalous. "
        "Labels: data/labels/samples.csv (86 hand-labeled visits).",
        ha="center",
        fontsize=8,
        color="#5a616b",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT} ({len(anomalous)} anomalous / {len(normal)} normal / {len(unlabeled)} unlabeled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

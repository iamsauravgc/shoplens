"""Epic 5: precision/recall from data/labels/samples.csv (labels filled in by hand).

Run:  .venv/Scripts/python scripts/score_labels.py   (from backend/)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent

from evaluation.metrics import precision_recall


def main() -> int:
    csv_path = REPO_ROOT / "data" / "labels" / "samples.csv"
    rows = list(csv.DictReader(csv_path.open()))

    unlabeled = [r for r in rows if r["label"].strip() == ""]
    if unlabeled:
        raise SystemExit(f"{len(unlabeled)} rows still unlabeled (first: row_index={unlabeled[0]['row_index']})")

    y_true = [r["label"].strip() in {"1", "true", "yes"} for r in rows]
    y_pred = [r["flagged"].strip() == "1" for r in rows]

    metrics = precision_recall(y_true, y_pred)
    metrics.update(
        {
            "labeled_rows": len(rows),
            "positives_in_labels": sum(y_true),
            "flagged_by_model": sum(y_pred),
        }
    )

    out = REPO_ROOT / "data" / "labels" / "results.json"
    out.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    print(f"\nsaved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

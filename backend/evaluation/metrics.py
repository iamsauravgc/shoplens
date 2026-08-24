from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


def load_detection_csv(csv_path: str | Path) -> list[dict]:
    with open(csv_path, newline="") as f:
        return [
            {**row, "frame_id": int(row["frame_id"])}
            for row in csv.DictReader(f)
        ]


def detection_metrics(rows: list[dict]) -> dict:
    errors = np.array([int(r["detected_count"]) - int(r["gt_count"]) for r in rows], dtype=np.float64)
    return {
        "frames": len(rows),
        "mae": round(float(np.abs(errors).mean()), 3),
        "mse": round(float((errors**2).mean()), 3),
        "rmse": round(float(np.sqrt((errors**2).mean())), 3),
    }


def threshold_mae_table(results_by_threshold: dict[float, float]) -> str:
    lines = ["| threshold | MAE |", "|---|---|"]
    for threshold in sorted(results_by_threshold):
        lines.append(f"| {threshold:.2f} | {results_by_threshold[threshold]:.2f} |")
    return "\n".join(lines)


def id_switch_rate(unique_ids: int, gt_persons: int | None = None) -> dict:
    # proxy metric from tracking.ipynb: fewer IDs on the same footage = fewer ID switches
    # TODO(epic-9 day 1): refine using short-track counting (cv.tracker.count_id_switches)
    metrics = {"unique_ids": unique_ids}
    if gt_persons is not None and gt_persons > 0:
        metrics["ids_per_gt_person"] = round(unique_ids / gt_persons, 3)
    return metrics


def precision_recall(y_true: list[bool], y_pred: list[bool]) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def format_results_table(detection: dict, tracking: dict, anomaly: dict) -> str:
    lines = [
        "| metric | value |",
        "|---|---|",
        f"| detection MAE | {detection.get('mae')} |",
        f"| detection RMSE | {detection.get('rmse')} |",
        f"| unique track IDs | {tracking.get('unique_ids')} |",
        f"| anomaly precision | {anomaly.get('precision')} |",
        f"| anomaly recall | {anomaly.get('recall')} |",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m evaluation.metrics <detection_results.csv>")
    print(detection_metrics(load_detection_csv(sys.argv[1])))

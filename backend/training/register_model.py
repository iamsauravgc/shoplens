from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient

from cv.anomaly import (
    DEFAULT_MODEL_PATH,
    DEFAULT_THRESHOLD_PATH,
    DEFAULT_ZONE_INDEX_PATH,
    MODELS_DIR,
    TrajectoryAutoencoder,
)

MODEL_NAME = "shoplens-autoencoder"


def best_run_metrics(experiment: str) -> dict:
    exp = mlflow.get_experiment_by_name(experiment)
    if exp is None:
        return {}
    runs = mlflow.search_runs(experiment_ids=[exp.experiment_id], order_by=["metrics.final_loss ASC"])
    if runs.empty:
        return {}
    row = runs.iloc[0]
    out = {"final_loss": float(row["metrics.final_loss"])}
    for key in ("train_error_p95", "test_error_p95"):
        if key in row and row[key] == row[key]:
            out[key] = float(row[key])
    return out


def main() -> int:
    if not DEFAULT_MODEL_PATH.exists():
        raise SystemExit(f"missing {DEFAULT_MODEL_PATH} — run training/train_autoencoder.py first")

    state = torch_load(DEFAULT_MODEL_PATH)
    model = TrajectoryAutoencoder()
    model.load_state_dict(state)
    model.eval()

    threshold = json.loads(DEFAULT_THRESHOLD_PATH.read_text())
    zone_index = json.loads(DEFAULT_ZONE_INDEX_PATH.read_text())

    mlflow.set_experiment("shoplens-autoencoder")
    metrics = best_run_metrics("shoplens-autoencoder")
    with mlflow.start_run(run_name="register-best-model") as run:
        mlflow.log_params(
            {
                "source": "exported artifacts from models/",
                "architecture": "4-8-4-2-4-8-4",
                "feature_dim": 4,
                "zone_count": len(zone_index),
            }
        )
        for k, v in metrics.items():
            mlflow.log_metric(f"train_{k}" if k == "final_loss" else k, v)
        mlflow.log_metric("anomaly_threshold", float(threshold.get("threshold", 0.0)))
        mlflow.pytorch.log_model(model, name="model", serialization_format="pickle")
        mlflow.log_artifact(str(DEFAULT_MODEL_PATH))
        mlflow.log_artifact(str(MODELS_DIR / "autoencoder.scaler.joblib"))
        mlflow.log_artifact(str(DEFAULT_THRESHOLD_PATH))
        mlflow.log_artifact(str(DEFAULT_ZONE_INDEX_PATH))
        run_id = run.info.run_id

    client = MlflowClient()
    result = mlflow.register_model(f"runs:/{run_id}/model", MODEL_NAME)
    client.set_model_version_tag(MODEL_NAME, result.version, "source_run", run_id)
    print(
        f"registered {MODEL_NAME} v{result.version} ({result.status})\n"
        f"  run: {run_id}\n"
        f"  threshold: {threshold.get('threshold')}\n"
        f"  zones: {len(zone_index)}\n"
        f"  view: mlflow ui --backend-store-uri sqlite:///mlflow.db"
    )
    return 0


def torch_load(path: Path):
    import torch

    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


if __name__ == "__main__":
    raise SystemExit(main())

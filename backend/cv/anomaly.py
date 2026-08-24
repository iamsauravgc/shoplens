from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn

logger = logging.getLogger(__name__)

FEATURE_DIM = 4
ANOMALY_PERCENTILE = 95
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "autoencoder.pth"

LOITERING_MIN_DWELL_SEC = 60.0
CROWD_SPIKE_RATIO = 2.0
CROWD_BASELINE_WINDOW = 50


class TrajectoryAutoencoder(nn.Module):
    # Input(4) -> 8 -> 4 -> 2 -> 4 -> 8 -> Output(4), per epics.md Epic 5 Day 3
    def __init__(self, dim: int = FEATURE_DIM):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(dim, 8),
            nn.ReLU(),
            nn.Linear(8, 4),
            nn.ReLU(),
            nn.Linear(4, 2),
        )
        self.decoder = nn.Sequential(
            nn.Linear(2, 4),
            nn.ReLU(),
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


def extract_trajectory_features(
    trajectories: dict,
    zones,
    frame_interval_sec: float,
) -> np.ndarray:
    """One row per (track_id, zone-visit): (zone_index, dwell_time, mean_velocity, direction_change_rate)."""
    # TODO(epic-5 day 2): implement using cv.zones.compute_zone_visits + per-point deltas;
    # encode zone_id as a stable integer index shared between training and inference
    raise NotImplementedError("Epic 5 Day 2")


def save_artifacts(model: TrajectoryAutoencoder, scaler: StandardScaler, model_path: Path = DEFAULT_MODEL_PATH) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_path)
    scaler_path = model_path.with_suffix(".scaler.joblib")
    import joblib

    joblib.dump(scaler, scaler_path)
    logger.info("saved model to %s and scaler to %s", model_path, scaler_path)


def load_model(model_path: Path = DEFAULT_MODEL_PATH) -> TrajectoryAutoencoder:
    model = TrajectoryAutoencoder()
    state = torch.load(model_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    return model


def load_scaler(model_path: Path = DEFAULT_MODEL_PATH) -> StandardScaler:
    import joblib

    return joblib.load(model_path.with_suffix(".scaler.joblib"))


def reconstruction_errors(model: TrajectoryAutoencoder, features_scaled: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        x = torch.tensor(features_scaled, dtype=torch.float32)
        recon = model(x)
        return ((recon - x) ** 2).mean(dim=1).numpy()


def anomaly_threshold(errors: np.ndarray, percentile: int = ANOMALY_PERCENTILE) -> float:
    return float(np.percentile(errors, percentile))


def score_trajectories(features_raw: np.ndarray, model_path: Path = DEFAULT_MODEL_PATH) -> list[dict]:
    model = load_model(model_path)
    scaler = load_scaler(model_path)
    scaled = scaler.transform(features_raw)
    errors = reconstruction_errors(model, scaled)
    threshold = anomaly_threshold(errors)
    return [
        {"row_index": i, "error": round(float(e), 6), "is_anomaly": bool(e > threshold)}
        for i, e in enumerate(errors)
    ]


def classify_loitering(dwell_seconds: float, mean_velocity: float) -> bool:
    # TODO(epic-6 day 1): calibrate LOITERING_* thresholds on manually labeled examples
    return dwell_seconds >= LOITERING_MIN_DWELL_SEC and mean_velocity < 1.0


def detect_crowd_spikes(counts_per_frame: list[int]) -> list[int]:
    # TODO(epic-6 day 1): rolling-baseline spike detector; tune CROWD_SPIKE_RATIO on labeled spikes
    raise NotImplementedError("Epic 6 Day 1")


def detect_zone_avoidance(zone_visitor_counts: dict[str, int], expected_zones: list[str], min_visitors: int = 1) -> list[str]:
    return [z for z in expected_zones if zone_visitor_counts.get(z, 0) < min_visitors]

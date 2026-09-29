from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn

from cv.zones import Zone, ZoneVisit, compute_zone_visits

logger = logging.getLogger(__name__)

FEATURE_DIM = 4
ANOMALY_PERCENTILE = 95
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "autoencoder.pth"
DEFAULT_THRESHOLD_PATH = MODELS_DIR / "threshold.json"
DEFAULT_ZONE_INDEX_PATH = MODELS_DIR / "zone_index.json"

# calibrated on the mall footage: genuine stand-stills dwell 38-48s with
# q15-q85 displacement speed 0.4-0.5 px/s; walkers of any length sit at >=1.7
LOITERING_MIN_DWELL_SEC = 30.0
LOITERING_MAX_STANDSTILL_SPEED = 1.5  # px/s
CROWD_SPIKE_RATIO = 2.0
CROWD_BASELINE_WINDOW = 50
AVOIDANCE_MIN_RATIO = 0.25  # a zone drawing <25% of typical zone traffic counts as skipped
AVOIDANCE_MIN_VISITORS = 5  # absolute ceiling too: <5 visitors is dead regardless of ratio
MIN_ZONE_TRAFFIC_FOR_AVOIDANCE = 10  # median traffic must be at least this before judging
DIRECTION_CHANGE_ANGLE_RAD = math.radians(60)


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


# --- feature extraction (must match notebooks/autoencoder_training.ipynb) ----

def zone_index_map(zones: list[Zone]) -> dict[str, int]:
    """Stable zone encoding: zones sorted by name -> index. Persisted with the model."""
    return {z.name: i for i, z in enumerate(sorted(zones, key=lambda z: z.name))}


def _velocity_and_turn_rate(points: list[dict], dwell_seconds: float) -> tuple[float, float]:
    if len(points) < 2 or dwell_seconds <= 0:
        return 0.0, 0.0
    dist = 0.0
    turns = 0
    prev_angle: float | None = None
    for a, b in zip(points, points[1:]):
        dx = b["cx"] - a["cx"]
        dy = b["cy"] - a["cy"]
        dist += math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        if prev_angle is not None:
            delta = abs(angle - prev_angle)
            delta = min(delta, 2 * math.pi - delta)
            if delta >= DIRECTION_CHANGE_ANGLE_RAD:
                turns += 1
        prev_angle = angle
    return dist / dwell_seconds, turns / dwell_seconds


def features_from_visits(
    visits: list[ZoneVisit],
    trajectories: dict,
    zones: list[Zone],
    zone_index: dict[str, int] | None = None,
) -> np.ndarray:
    """One row per visit: (zone_index, dwell_time, mean_velocity, direction_change_rate).

    Rows align 1:1 with the `visits` argument (same order).
    """
    if not visits:
        return np.empty((0, FEATURE_DIM), dtype=np.float64)
    index = zone_index if zone_index is not None else zone_index_map(zones)
    name_of = {z.zone_id: z.name for z in zones}

    rows = []
    for v in visits:
        points = visit_points(trajectories, v)
        velocity, turn_rate = _velocity_and_turn_rate(points, v.dwell_seconds)
        zone_name = name_of.get(v.zone_id, "")
        rows.append(
            [
                float(index.get(zone_name, len(index))),
                float(v.dwell_seconds),
                float(velocity),
                float(turn_rate),
            ]
        )
    return np.asarray(rows, dtype=np.float64).reshape(-1, FEATURE_DIM)


def extract_trajectory_features(
    trajectories: dict,
    zones: list[Zone],
    frame_interval_sec: float,
    zone_index: dict[str, int] | None = None,
) -> np.ndarray:
    """One row per (track_id, zone-visit): (zone_index, dwell_time, mean_velocity, direction_change_rate)."""
    visits = compute_zone_visits(trajectories, zones, frame_interval_sec)
    return features_from_visits(visits, trajectories, zones, zone_index)


# --- artifacts ---------------------------------------------------------------

def save_artifacts(model: TrajectoryAutoencoder, scaler: StandardScaler, model_path: Path = DEFAULT_MODEL_PATH) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_path)
    scaler_path = model_path.with_suffix(".scaler.joblib")
    import joblib

    joblib.dump(scaler, scaler_path)
    logger.info("saved model to %s and scaler to %s", model_path, scaler_path)


def save_threshold(threshold: float, meta: dict | None = None, path: Path = DEFAULT_THRESHOLD_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"threshold": threshold, "percentile": ANOMALY_PERCENTILE, **(meta or {})}, indent=2))


def load_threshold(path: Path = DEFAULT_THRESHOLD_PATH) -> float | None:
    if not path.exists():
        return None
    return float(json.loads(path.read_text())["threshold"])


def save_zone_index(index: dict[str, int], path: Path = DEFAULT_ZONE_INDEX_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2))


def load_zone_index(path: Path = DEFAULT_ZONE_INDEX_PATH) -> dict[str, int] | None:
    if not path.exists():
        return None
    return {k: int(v) for k, v in json.loads(path.read_text()).items()}


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
    """Score visits with the trained autoencoder. Uses the threshold saved at training time."""
    if features_raw.size == 0:
        return []
    model = load_model(model_path)
    scaler = load_scaler(model_path)
    scaled = scaler.transform(features_raw)
    errors = reconstruction_errors(model, scaled)
    threshold = load_threshold(model_path.parent / "threshold.json")
    if threshold is None:
        threshold = anomaly_threshold(errors)
        logger.warning("no saved threshold — falling back to p%d of these errors", ANOMALY_PERCENTILE)
    return [
        {
            "row_index": i,
            "error": round(float(e), 6),
            "score": round(float(e), 6),
            "is_anomaly": bool(e > threshold),
        }
        for i, e in enumerate(errors)
    ]


# --- rule-based detectors ----------------------------------------------------

def visit_points(trajectories: dict, visit: ZoneVisit) -> list[dict]:
    """Trajectory points inside the visit's frame window (entry..exit inclusive)."""
    key = str(visit.track_id)
    points = trajectories.get(key, trajectories.get(visit.track_id, []))
    return [p for p in points if visit.entry_frame <= int(p["frame"]) <= visit.exit_frame]


def standstill_speed(points: list[dict], dwell_seconds: float) -> float:
    """Displacement between the 15% and 85% quantile points, per second.

    Raw path-length speed is useless here: per-frame centroid jitter makes a
    standing person look like they move 6-30 px/s. Measuring only the middle
    70% of the visit ignores entry/exit transients (someone who stands for 40s
    then walks off has a large net displacement but is still a loiterer).
    """
    if len(points) < 3 or dwell_seconds <= 0:
        return 0.0
    a = points[int(0.15 * (len(points) - 1))]
    b = points[int(0.85 * (len(points) - 1))]
    return math.hypot(b["cx"] - a["cx"], b["cy"] - a["cy"]) / dwell_seconds


def classify_loitering(dwell_seconds: float, standstill_speed_px_s: float) -> bool:
    # TODO(epic-6 day 1): calibrate thresholds on manually labeled examples
    return dwell_seconds >= LOITERING_MIN_DWELL_SEC and standstill_speed_px_s < LOITERING_MAX_STANDSTILL_SPEED


def detect_crowd_spikes(
    counts_per_frame: list[int],
    baseline_window: int = CROWD_BASELINE_WINDOW,
    ratio: float = CROWD_SPIKE_RATIO,
) -> list[int]:
    """Indices (into counts_per_frame) where the count jumps above `ratio` x rolling baseline.

    One spike per consecutive burst: the peak frame of the run is reported.
    """
    candidates: list[int] = []
    for i, count in enumerate(counts_per_frame):
        history = counts_per_frame[max(0, i - baseline_window) : i]
        if len(history) < 5:
            continue
        baseline = sum(history) / len(history)
        if baseline > 0 and count >= ratio * baseline and count >= baseline + 2:
            candidates.append(i)

    spikes: list[int] = []
    run: list[int] = []
    for idx in candidates:
        if run and idx == run[-1] + 1:
            run.append(idx)
        else:
            if run:
                spikes.append(max(run, key=lambda j: counts_per_frame[j]))
            run = [idx]
    if run:
        spikes.append(max(run, key=lambda j: counts_per_frame[j]))
    return spikes


def detect_zone_avoidance(
    zone_visitor_counts: dict[str, int],
    expected_zones: list[str],
    min_ratio: float = AVOIDANCE_MIN_RATIO,
    min_visitors: int = AVOIDANCE_MIN_VISITORS,
) -> list[str]:
    """Zones that are 'consistently skipped': dead (< min_visitors) or drawing
    less than `min_ratio` x the median zone's traffic.

    Absolute-zero alone is too brittle — background flickers near a frame edge
    can register a handful of pass-through visits. Requiring a zone to sit far
    below typical traffic matches the epics.md definition ('zone consistently
    skipped').
    """
    if len(expected_zones) < 2:
        return []
    counts = [zone_visitor_counts.get(z, 0) for z in expected_zones]
    baseline = float(np.median(counts))
    if baseline < MIN_ZONE_TRAFFIC_FOR_AVOIDANCE:
        return []  # not enough overall traffic to judge avoidance
    return [z for z in expected_zones if zone_visitor_counts.get(z, 0) < max(min_visitors, baseline * min_ratio)]

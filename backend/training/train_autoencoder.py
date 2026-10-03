from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler

from app.db import fetch_zones
from cv.anomaly import (
    ANOMALY_PERCENTILE,
    DEFAULT_MODEL_PATH,
    MODELS_DIR,
    TrajectoryAutoencoder,
    anomaly_threshold,
    features_from_visits,
    save_artifacts,
    save_threshold,
    save_zone_index,
    zone_index_map,
)
from cv.zones import Zone, compute_zone_visits

FRAME_INTERVAL_SEC = 1 / 30  # trajectory frames are source-frame units (matches pipeline 1/fps)
EPOCHS = 400  # 100 was too early — loss still ~1.0; 400 converges to ~0.5 in seconds on CPU
LR = 1e-3
SEED = 42


def load_trajectories(path: Path) -> dict:
    raw = json.loads(path.read_text())
    return raw.get("trajectories", raw)


def build_zones() -> list[Zone]:
    rows = fetch_zones()
    if not rows:
        raise SystemExit("No zones in the database — draw and save zones in the Zones tab first.")
    return [
        Zone(
            zone_id=str(r["id"]),
            name=r["name"],
            polygon=[(float(p["x"]), float(p["y"])) for p in r["polygon"]],
        )
        for r in rows
    ]


def main() -> int:
    traj_path = REPO_ROOT / "data" / "trajectories.json"
    if not traj_path.exists():
        raise SystemExit(f"Missing {traj_path} — download it from Drive into data/ first.")

    trajectories = load_trajectories(traj_path)
    zones = build_zones()
    print(f"tracks={len(trajectories)} zones={[z.name for z in zones]}")

    visits = compute_zone_visits(trajectories, zones, FRAME_INTERVAL_SEC)
    zone_index = zone_index_map(zones)
    features = features_from_visits(visits, trajectories, zones, zone_index)
    print(f"zone visits (feature rows): {len(features)}")
    if len(features) < 40:
        print("WARNING: fewer than 40 visits — the autoencoder will be poorly constrained.")

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    rng = np.random.default_rng(SEED)
    perm = rng.permutation(len(scaled))
    split = int(0.8 * len(perm))
    train_x, test_x = scaled[perm[:split]], scaled[perm[split:]]

    model = TrajectoryAutoencoder()
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = torch.nn.MSELoss()
    x_train = torch.tensor(train_x, dtype=torch.float32)

    mlflow.set_experiment("shoplens-autoencoder")
    run = mlflow.start_run()
    mlflow.log_params(
        {
            "epochs": EPOCHS,
            "lr": LR,
            "train_rows": len(train_x),
            "test_rows": len(test_x),
            "zones": ",".join(z.name for z in zones),
            "seed": SEED,
        }
    )

    losses = []
    t0 = time.time()
    for epoch in range(EPOCHS):
        opt.zero_grad()
        recon = model(x_train)
        loss = loss_fn(recon, x_train)
        loss.backward()
        opt.step()
        losses.append(loss.item())
        if epoch % 10 == 0:
            mlflow.log_metric("train_loss", float(loss), step=epoch)
            print(f"epoch {epoch:4d}  loss {float(loss):.5f}")

    model.eval()
    with torch.no_grad():
        x_test = torch.tensor(test_x, dtype=torch.float32)
        test_errors = ((model(x_test) - x_test) ** 2).mean(dim=1).numpy()
        train_errors = ((model(x_train) - x_train) ** 2).mean(dim=1).numpy()

    threshold = anomaly_threshold(train_errors)  # p95 on the training set
    test_p95 = anomaly_threshold(test_errors)
    mlflow.log_metric("final_loss", float(loss))
    mlflow.log_metric("train_error_p95", threshold)
    mlflow.log_metric("test_error_p95", test_p95)

    save_artifacts(model, scaler, DEFAULT_MODEL_PATH)
    save_threshold(threshold, {"train_error_p95": threshold, "test_error_p95": test_p95, "train_rows": len(train_x)})
    save_zone_index(zone_index)
    mlflow.log_artifact(str(DEFAULT_MODEL_PATH.parent / "threshold.json"))
    mlflow.log_artifact(str(DEFAULT_MODEL_PATH.parent / "zone_index.json"))

    out_dir = REPO_ROOT / "data" / "out" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(losses)
    axes[0].set_title("training loss")
    axes[0].set_xlabel("epoch")
    axes[1].hist(test_errors, bins=30)
    axes[1].axvline(threshold, color="r", label=f"p{ANOMALY_PERCENTILE} threshold")
    axes[1].set_title("test reconstruction error")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(out_dir / "autoencoder_training.png")
    plt.close(fig)

    run_id = mlflow.active_run().info.run_id
    mlflow.end_run()

    flagged = int((test_errors > threshold).sum())
    print(
        f"\nDONE in {time.time() - t0:.1f}s | rows={len(features)} train={len(train_x)} test={len(test_x)}\n"
        f"threshold(p{ANOMALY_PERCENTILE} of train errors)={threshold:.6f}  test_p95={test_p95:.6f}  "
        f"test rows above threshold={flagged}/{len(test_x)}\n"
        f"model={DEFAULT_MODEL_PATH}\nmlflow run={run_id} (view: mlflow ui --backend-store-uri mlruns)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

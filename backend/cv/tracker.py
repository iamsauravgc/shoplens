import logging

from deep_sort_realtime.deepsort_tracker import DeepSort

from cv.detector import xyxy_to_xywh

logger = logging.getLogger(__name__)

# tuned in notebooks/tracking.ipynb — TODO(epic-2): copy final values from the tuning cell
BEST_MAX_AGE = 30
BEST_N_INIT = 3


def make_tracker(max_age: int = BEST_MAX_AGE, n_init: int = BEST_N_INIT) -> DeepSort:
    return DeepSort(max_age=max_age, n_init=n_init, embedder_gpu=False)


def update_tracks(
    tracker: DeepSort,
    detections_xyxy,
    scores,
    frame,
):
    ds_input = [
        (xyxy_to_xywh(box), float(score), "person")
        for box, score in zip(detections_xyxy, scores)
    ]
    tracks = tracker.update_tracks(ds_input, frame=frame)

    out = []
    for t in tracks:
        if not t.is_confirmed():
            continue
        x1, y1, x2, y2 = t.to_tlbr()
        out.append(
            {
                "track_id": int(t.track_id),
                "bbox": (float(x1), float(y1), float(x2), float(y2)),
                "centroid": ((float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2),
            }
        )
    return out


def build_trajectories(frame_tracks: dict) -> tuple[dict, dict]:
    trajectories = {}
    for frame_idx, persons in sorted(frame_tracks.items()):
        for p in persons:
            trajectories.setdefault(p["track_id"], []).append(
                {"frame": int(frame_idx), "cx": round(p["centroid"][0], 2), "cy": round(p["centroid"][1], 2)}
            )
    return trajectories, frame_tracks


def count_id_switches(trajectories: dict, min_points: int = 5) -> int:
    # proxy metric from tracking.ipynb: short-lived tracks are likely ID switches
    return sum(1 for points in trajectories.values() if len(points) < min_points)

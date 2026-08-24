import asyncio
import json
import logging
import tempfile
from pathlib import Path

import cv2

from app.config import get_redis
from app.db import (
    fetch_zones,
    insert_anomalies,
    insert_report,
    update_video_status,
    upsert_analytics,
)
from app.services.report import generate_report
from app.storage import download_to
from cv.anomaly import classify_loitering, detect_zone_avoidance
from cv.blur import blur_faces
from cv.detector import BEST_CONF, detect_persons
from cv.heatmap import export_png, generate_heatmap, heatmap_response_path, overlay_heatmap
from cv.tracker import build_trajectories, make_tracker, update_tracks
from cv.zones import Zone, compute_zone_visits, summarize_zones

logger = logging.getLogger(__name__)

QUEUE_NAME = "video"
PROCESS_VIDEO_TIMEOUT = "1h"
TOTAL_STEPS = 7
FRAME_SAMPLE_INTERVAL = 5
MAX_VIDEO_SECONDS = 120
DEFAULT_FPS = 30.0


def _set_progress(job_id: str, step: int, message: str, state: str = "processing") -> None:
    payload = {"step": step, "total_steps": TOTAL_STEPS, "message": message, "state": state}
    get_redis().set(f"job:{job_id}:progress", json.dumps(payload))


def _read_sampled_frames(video_path: Path) -> tuple[list[tuple[int, "cv2.Mat"]], float]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Video is corrupted or unreadable")

    fps = cap.get(cv2.CAP_PROP_FPS) or DEFAULT_FPS
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count and (frame_count / fps) > MAX_VIDEO_SECONDS:
        cap.release()
        raise ValueError(f"Video longer than {MAX_VIDEO_SECONDS} seconds")

    frames = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % FRAME_SAMPLE_INTERVAL == 0:
            frames.append((idx, frame))
        idx += 1
    cap.release()
    if not frames:
        raise ValueError("No frames could be read from the video")
    return frames, fps


def _detect_and_blur(frames):
    # privacy: blur faces immediately after detection, before anything else touches the frame
    annotated = []
    for idx, frame in frames:
        boxes = detect_persons(frame, conf=BEST_CONF)
        annotated.append((idx, blur_faces(frame, boxes), boxes))
    return annotated


def _track(annotated_frames):
    tracker = make_tracker()
    frame_data = {}
    for idx, blurred_frame, boxes in annotated_frames:
        scores = [BEST_CONF] * len(boxes)
        persons = update_tracks(tracker, boxes, scores, blurred_frame)
        frame_data[idx] = persons
    trajectories, _ = build_trajectories(frame_data)
    return trajectories, frame_data


def _zone_analytics(trajectories: dict, zones_raw: list[dict], fps: float):
    zones = [
        Zone(
            zone_id=str(z["id"]),
            name=z.get("name", str(z["id"])),
            polygon=[(float(p["x"]), float(p["y"])) for p in z["polygon"]],
        )
        for z in zones_raw
    ]
    frame_interval_sec = FRAME_SAMPLE_INTERVAL / fps
    visits = compute_zone_visits(trajectories, zones, frame_interval_sec)
    summary = summarize_zones(visits, zones)
    return zones, visits, summary


def _generate_heatmaps(annotated_frames, frame_data, zones, job_id: str, out_dir: Path) -> list[str]:
    # TODO(epic-4 day 3): time-segmented heatmaps need a wall-clock mapping; for now only full
    positions = []
    base_frame = annotated_frames[0][1]
    for _, persons in frame_data.items():
        positions.extend(p["centroid"] for p in persons)
    heat = generate_heatmap(base_frame.shape, positions)
    overlay = overlay_heatmap(base_frame, heat)
    local_png = export_png(overlay, out_dir / f"{job_id}_full.png")
    from app.storage import upload_file

    key = heatmap_response_path(job_id, "full")
    upload_file(local_png, key, content_type="image/png")
    return [key]


def _flag_anomalies(visits, summary, expected_zones) -> list[dict]:
    events = []
    by_track_zone: dict[tuple[int, str], list[float]] = {}
    velocities_by_visit = {}  # TODO(epic-6 day 2): wire real velocity features via extract_trajectory_features
    for v in visits:
        by_track_zone.setdefault((v.track_id, v.zone_id), []).append(v.dwell_seconds)

    loitering_rows = [
        {"track_id": tid, "zone_id": zid, "dwell_seconds": max(dwells)}
        for (tid, zid), dwells in by_track_zone.items()
    ]
    for row in loitering_rows:
        if classify_loitering(row["dwell_seconds"], mean_velocity=velocities_by_visit.get(row["track_id"], 1.0)):
            events.append({"anomaly_type": "loitering", "zone_id": row["zone_id"], "frame": None, "details": row})

    avoided = detect_zone_avoidance({z: s["unique_visitors"] for z, s in summary.items()}, expected_zones)
    for zone_id in avoided:
        events.append({"anomaly_type": "zone_avoidance", "zone_id": zone_id, "frame": None, "details": {}})

    # crowd spikes require per-frame counts — see cv.anomaly.detect_crowd_spikes (TODO epic-6 day 1)
    return events


def process_video(job_id: str, storage_key: str, store_id: str = "default"):
    logger.info("pipeline started for %s", job_id)
    tmp_dir = Path(tempfile.mkdtemp(prefix="shoplens_"))
    video_path = tmp_dir / f"{job_id}.mp4"

    try:
        _set_progress(job_id, 1, "Downloading video...")
        download_to(storage_key, video_path)

        _set_progress(job_id, 1, "Reading frames (every 5th)...")
        frames, fps = _read_sampled_frames(video_path)

        _set_progress(job_id, 2, "Detecting people + blurring faces...")
        annotated = _detect_and_blur(frames)

        _set_progress(job_id, 3, "Tracking IDs with DeepSORT...")
        trajectories, frame_data = _track(annotated)

        _set_progress(job_id, 4, "Computing zone analytics...")
        zones_raw = fetch_zones(store_id)
        zones, visits, summary = _zone_analytics(trajectories, zones_raw, fps)

        _set_progress(job_id, 5, "Generating heatmap...")
        heatmap_keys = _generate_heatmaps(annotated, frame_data, zones, job_id, tmp_dir)

        _set_progress(job_id, 6, "Scoring anomalies...")
        anomaly_events = _flag_anomalies(visits, summary, [z.zone_id for z in zones])

        analytics_payload = {
            "video_id": job_id,
            "frames_processed": len(frames),
            "fps": fps,
            "unique_visitors": len(trajectories),
            "zone_summary": summary,
            "heatmap_keys": heatmap_keys,
        }
        upsert_analytics({"video_id": job_id, "payload": analytics_payload})
        insert_anomalies([{**e, "video_id": job_id} for e in anomaly_events])

        _set_progress(job_id, 7, "Generating insight report...")
        report_content = asyncio.run(generate_report(analytics_payload))
        insert_report({"video_id": job_id, "content": report_content, "model": "llama-3.3-70b-versatile"})

        update_video_status(job_id, "done")
        _set_progress(job_id, TOTAL_STEPS, "Done", state="complete")
        logger.info("pipeline finished for %s", job_id)
    except Exception as exc:
        logger.exception("pipeline failed for %s", job_id)
        update_video_status(job_id, "failed", error=str(exc))
        _set_progress(job_id, 0, str(exc), state="failed")
        # TODO(epic-8 day 5): retry logic — re-enqueue transient failures, fail permanently on corrupt video
        raise
    finally:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)

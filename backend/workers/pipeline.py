import asyncio
import logging
import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings
from app.db import (
    fetch_video,
    fetch_zones,
    insert_anomalies,
    insert_report,
    set_job_progress,
    update_video_status,
    upsert_analytics,
)
from app.services.report import generate_report
from app.storage import download_to
from cv.blur import blur_faces
from cv.detector import BEST_CONF, detect_persons
from cv.heatmap import export_png, generate_heatmap, heatmap_response_path, overlay_heatmap, split_positions_by_segment
from cv.tracker import build_trajectories, make_tracker, update_tracks
from cv.zones import Zone, compute_zone_visits, peak_hour_per_zone, summarize_zones

logger = logging.getLogger(__name__)

QUEUE_NAME = "video"
PROCESS_VIDEO_TIMEOUT = "1h"
TOTAL_STEPS = 7
FRAME_SAMPLE_INTERVAL = 5
MAX_VIDEO_SECONDS = 120
DEFAULT_FPS = 30.0


def _set_progress(job_id: str, step: int, message: str, state: str = "processing") -> None:
    set_job_progress(job_id, step, TOTAL_STEPS, message, state)


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


def _zone_analytics(trajectories: dict, zones_raw: list[dict], fps: float, video_started_at=None):
    zones = [
        Zone(
            zone_id=str(z["id"]),
            name=z.get("name", str(z["id"])),
            polygon=[(float(p["x"]), float(p["y"])) for p in z["polygon"]],
        )
        for z in zones_raw
    ]
    # frame indices are source-frame units, so one source frame = 1/fps seconds
    frame_interval_sec = 1.0 / fps
    visits = compute_zone_visits(trajectories, zones, frame_interval_sec)
    summary = summarize_zones(visits, zones)
    for zone_id, hour in peak_hour_per_zone(visits, video_started_at, fps).items():
        if zone_id in summary:
            summary[zone_id]["peak_hour"] = hour
    return zones, visits, summary


def _generate_heatmaps(annotated_frames, frame_data, zones, job_id: str, out_dir: Path) -> list[str]:
    from app.storage import upload_file

    base_frame = annotated_frames[0][1]
    positions: list[tuple[int, tuple[float, float]]] = []
    for idx, persons in frame_data.items():
        positions.extend((idx, p["centroid"]) for p in persons)

    keys = []
    for segment, pts in split_positions_by_segment(positions).items():
        if not pts:
            continue
        heat = generate_heatmap(base_frame.shape, pts)
        overlay = overlay_heatmap(base_frame, heat)
        local_png = export_png(overlay, out_dir / f"{job_id}_{segment}.png")
        key = heatmap_response_path(job_id, segment)
        upload_file(local_png, key, content_type="image/png")
        keys.append(key)
    return keys


def _flag_anomalies(visits, summary, trajectories, zones, frame_data, expected_zones) -> list[dict]:
    from cv.anomaly import (
        DEFAULT_MODEL_PATH,
        classify_loitering,
        detect_crowd_spikes,
        detect_zone_avoidance,
        features_from_visits,
        load_zone_index,
        score_trajectories,
        standstill_speed,
        visit_points,
        zone_index_map,
    )

    events: list[dict] = []
    zone_index = load_zone_index() or zone_index_map(zones)
    features = features_from_visits(visits, trajectories, zones, zone_index)

    if DEFAULT_MODEL_PATH.exists():
        scores = score_trajectories(features)
        for visit, score in zip(visits, scores):
            if score["is_anomaly"]:
                events.append(
                    {
                        "anomaly_type": "autoencoder",
                        "zone_id": visit.zone_id,
                        "frame": visit.entry_frame,
                        "details": {
                            "track_id": visit.track_id,
                            "dwell_seconds": visit.dwell_seconds,
                            "reconstruction_error": score["error"],
                        },
                    }
                )
    else:
        logger.warning("models missing — run training/train_autoencoder.py (skipping autoencoder scoring)")

    for visit in visits:
        dwell_seconds = float(visit.dwell_seconds)
        speed = standstill_speed(visit_points(trajectories, visit), dwell_seconds)
        if classify_loitering(dwell_seconds, speed):
            events.append(
                {
                    "anomaly_type": "loitering",
                    "zone_id": visit.zone_id,
                    "frame": visit.entry_frame,
                    "details": {
                        "track_id": visit.track_id,
                        "dwell_seconds": dwell_seconds,
                        "standstill_speed": round(speed, 2),
                    },
                }
            )

    ordered_frames = sorted(frame_data)
    counts = [len(frame_data[f]) for f in ordered_frames]
    for spike_idx in detect_crowd_spikes(counts):
        events.append(
            {
                "anomaly_type": "crowd_spike",
                "zone_id": None,
                "frame": ordered_frames[spike_idx],
                "details": {"persons": counts[spike_idx], "baseline_window": 50},
            }
        )

    visitor_counts = {z: s["unique_visitors"] for z, s in summary.items()}
    for zone_id in detect_zone_avoidance(visitor_counts, expected_zones):
        events.append(
            {
                "anomaly_type": "zone_avoidance",
                "zone_id": zone_id,
                "frame": None,
                "details": {
                    "zone_visitors": visitor_counts.get(zone_id, 0),
                    "typical_zone_visitors": int(np.median([visitor_counts.get(z, 0) for z in expected_zones])),
                },
            }
        )
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
        video = fetch_video(job_id) or {}
        zones, visits, summary = _zone_analytics(trajectories, zones_raw, fps, video.get("created_at"))

        _set_progress(job_id, 5, "Generating heatmap...")
        heatmap_keys = _generate_heatmaps(annotated, frame_data, zones, job_id, tmp_dir)

        _set_progress(job_id, 6, "Scoring anomalies...")
        anomaly_events = _flag_anomalies(visits, summary, trajectories, zones, frame_data, [z.zone_id for z in zones])

        analytics_payload = {
            "video_id": job_id,
            "frames_processed": len(frames),
            "fps": fps,
            "unique_visitors": len(trajectories),
            "zone_summary": summary,
            "zone_names": {z.zone_id: z.name for z in zones},
            "heatmap_keys": heatmap_keys,
        }
        upsert_analytics({"video_id": job_id, "payload": analytics_payload})
        insert_anomalies([{**e, "video_id": job_id} for e in anomaly_events])

        _set_progress(job_id, 7, "Generating insight report...")
        if get_settings().groq_api_key:
            report_content = asyncio.run(generate_report(analytics_payload))
            insert_report({"video_id": job_id, "content": report_content, "model": "llama-3.3-70b-versatile"})
        else:
            logger.info("GROQ_API_KEY not set — skipping report generation")

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

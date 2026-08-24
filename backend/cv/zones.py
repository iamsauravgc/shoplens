from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Zone:
    zone_id: str
    name: str
    polygon: list[tuple[float, float]]


@dataclass
class ZoneVisit:
    track_id: int
    zone_id: str
    entry_frame: int
    exit_frame: int
    dwell_seconds: float


def point_in_polygon(point: tuple[float, float], polygon) -> bool:
    contour = np.array(polygon, dtype=np.float32).reshape(-1, 2)
    return cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), False) >= 0


def assign_zone(point: tuple[float, float], zones: list[Zone]) -> str | None:
    for zone in zones:
        if point_in_polygon(point, zone.polygon):
            return zone.zone_id
    return None


def compute_zone_visits(
    trajectories: dict,
    zones: list[Zone],
    frame_interval_sec: float,
    min_frames: int = 3,
) -> list[ZoneVisit]:
    # TODO(epic-3 day 4): tune min_frames so a person walking past a zone edge isn't counted as a visit
    visits: list[ZoneVisit] = []
    for raw_id, points in trajectories.items():
        track_id = int(raw_id)
        current_zone: str | None = None
        entry_frame = 0
        last_frame = 0
        runs: list[tuple[str | None, int, int]] = []
        for pt in points:
            frame = int(pt["frame"])
            zone_id = assign_zone((pt["cx"], pt["cy"]), zones)
            if zone_id != current_zone:
                if current_zone is not None:
                    runs.append((current_zone, entry_frame, last_frame))
                current_zone = zone_id
                entry_frame = frame
            last_frame = frame
        if current_zone is not None:
            runs.append((current_zone, entry_frame, last_frame))
        for zone_id, f0, f1 in runs:
            frames_in = f1 - f0 + 1
            if zone_id is None or frames_in < min_frames:
                continue
            visits.append(
                ZoneVisit(
                    track_id=track_id,
                    zone_id=zone_id,
                    entry_frame=f0,
                    exit_frame=f1,
                    dwell_seconds=round(frames_in * frame_interval_sec, 2),
                )
            )
    return visits


def summarize_zones(visits: list[ZoneVisit], all_zones: list[Zone] | None = None) -> dict:
    summary: dict[str, dict] = {}
    zone_ids = {v.zone_id for v in visits}
    if all_zones:
        zone_ids.update(z.zone_id for z in all_zones)
    for zone_id in sorted(zone_ids):
        zone_visits = [v for v in visits if v.zone_id == zone_id]
        dwells = [v.dwell_seconds for v in zone_visits]
        summary[zone_id] = {
            "unique_visitors": len({v.track_id for v in zone_visits}),
            "total_visits": len(zone_visits),
            "avg_dwell_seconds": round(float(np.mean(dwells)), 2) if dwells else 0.0,
        }
    return summary


def peak_hour_per_zone(visits: list[ZoneVisit], video_started_at) -> dict:
    # TODO(epic-3 day 5): map each visit's entry frame to wall-clock time using video_started_at,
    # bucket into hours, return {zone_id: peak_hour}
    raise NotImplementedError("Epic 3 Day 5")

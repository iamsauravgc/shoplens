import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Response

from app.db import fetch_zones
from app.storage import object_exists, read_bytes
from cv.heatmap import heatmap_response_path, overlay_zones
from cv.zones import Zone

router = APIRouter()

VALID_SEGMENTS = {"full", "morning", "afternoon", "evening"}


def _zone_objects() -> list[Zone]:
    return [
        Zone(zone_id=str(r["id"]), name=r["name"], polygon=[(float(p["x"]), float(p["y"])) for p in r["polygon"]])
        for r in fetch_zones()
    ]


@router.get("/heatmap/{job_id}")
def get_heatmap(job_id: str, time_range: str = "full"):
    if time_range not in VALID_SEGMENTS:
        raise HTTPException(status_code=400, detail=f"time_range must be one of {sorted(VALID_SEGMENTS)}")
    key = heatmap_response_path(job_id, time_range)
    if not object_exists(key):
        raise HTTPException(status_code=404, detail=f"Heatmap not ready for {job_id} ({time_range})")
    raw = read_bytes(key)
    zones = _zone_objects()
    if not zones:
        return Response(content=raw, media_type="image/png")
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return Response(content=raw, media_type="image/png")
    ok, buf = cv2.imencode(".png", overlay_zones(frame, zones))
    return Response(content=buf.tobytes() if ok else raw, media_type="image/png")

from fastapi import APIRouter, HTTPException, Response

from app.storage import object_exists, read_bytes
from cv.heatmap import heatmap_response_path

router = APIRouter()

VALID_SEGMENTS = {"full", "morning", "afternoon", "evening"}


@router.get("/heatmap/{job_id}")
def get_heatmap(job_id: str, time_range: str = "full"):
    if time_range not in VALID_SEGMENTS:
        raise HTTPException(status_code=400, detail=f"time_range must be one of {sorted(VALID_SEGMENTS)}")
    key = heatmap_response_path(job_id, time_range)
    if not object_exists(key):
        raise HTTPException(status_code=404, detail=f"Heatmap not ready for {job_id} ({time_range})")
    return Response(content=read_bytes(key), media_type="image/png")

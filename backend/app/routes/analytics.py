from fastapi import APIRouter, HTTPException

from app.db import fetch_anomalies, fetch_analytics

router = APIRouter()


@router.get("/analytics/{job_id}")
def get_analytics(job_id: str):
    row = fetch_analytics(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No analytics for {job_id}")
    payload = row.get("payload") or {}
    return {
        "video_id": job_id,
        "frames_processed": payload.get("frames_processed"),
        "unique_visitors": payload.get("unique_visitors"),
        "zone_summary": payload.get("zone_summary", {}),
        "zone_names": payload.get("zone_names", {}),
        "heatmap_keys": payload.get("heatmap_keys", []),
        "payload": payload,
        "anomalies": fetch_anomalies(job_id),
    }

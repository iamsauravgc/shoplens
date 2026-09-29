from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db import create_zone, delete_zone, fetch_zones

router = APIRouter()


class ZoneIn(BaseModel):
    name: str
    polygon: list[dict]
    store_id: str = "default"


@router.get("/zones")
def list_zones(store_id: str = "default"):
    return fetch_zones(store_id)


@router.post("/zones", status_code=201)
def save_zone(body: ZoneIn):
    if len(body.polygon) < 3:
        raise HTTPException(status_code=400, detail="polygon needs at least 3 points")
    return create_zone(body.name, body.polygon, body.store_id)


@router.delete("/zones/{zone_id}", status_code=204)
def remove_zone(zone_id: str):
    if not delete_zone(zone_id):
        raise HTTPException(status_code=404, detail=f"Unknown zone {zone_id}")


@router.get("/zones/frame")
def zone_frame():
    frames_dir = get_settings().data_dir / "mall_dataset" / "frames"
    candidates = [frames_dir / "seq_000001.jpg"]
    if frames_dir.exists():
        candidates.extend(sorted(frames_dir.glob("*.jpg"))[:1])
    for path in candidates:
        if path.exists():
            return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="No reference frame available")

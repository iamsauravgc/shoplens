from fastapi import APIRouter, HTTPException

from app.db import get_job_progress

router = APIRouter()

TERMINAL_STATES = {"complete", "failed"}


@router.get("/status/{job_id}")
def get_status(job_id: str):
    progress = get_job_progress(job_id)
    if progress is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")
    return {"job_id": job_id, **progress}

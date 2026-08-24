import json

from fastapi import APIRouter, HTTPException
from rq.job import Job, NoSuchJobError

from app.config import get_redis

router = APIRouter()

PROGRESS_KEY_TEMPLATE = "job:{job_id}:progress"
TERMINAL_STATES = {"complete", "failed"}


def _read_progress(job_id: str) -> dict | None:
    raw = get_redis().get(PROGRESS_KEY_TEMPLATE.format(job_id=job_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


@router.get("/status/{job_id}")
def get_status(job_id: str):
    progress = _read_progress(job_id)
    if progress and progress.get("state") in TERMINAL_STATES:
        return {"job_id": job_id, **progress}

    try:
        job = Job.fetch(job_id, connection=get_redis())
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")

    state = job.get_status()  # queued / started / deferred / finished / failed
    if progress is None:
        progress = {"step": 0, "total_steps": 7, "message": "", "state": "processing"}
    if state in ("finished", "failed"):
        progress["state"] = "complete" if state == "finished" else "failed"
        if state == "failed":
            progress["message"] = str(job.exc_info or "Job failed")
    return {"job_id": job_id, **progress}

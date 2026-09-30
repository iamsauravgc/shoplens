from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import fetch_report, get_job_progress
from app.services.report import generate_and_store_report

router = APIRouter()

ACTIVE_STATES = {"queued", "processing"}


class GenerateReportRequest(BaseModel):
    video_id: str


@router.get("/report/{job_id}")
def get_report(job_id: str):
    report = fetch_report(job_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No report for job {job_id}")
    return report


@router.post("/reports/generate")
async def generate_report(req: GenerateReportRequest):
    progress = get_job_progress(req.video_id)
    if progress and progress["state"] in ACTIVE_STATES:
        raise HTTPException(status_code=409, detail="Job is still running — wait for it to finish")
    report = await generate_and_store_report(req.video_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No analytics found for {req.video_id}")
    return report

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import fetch_report
from app.services.report import generate_and_store_report

router = APIRouter()


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
    # TODO(epic-7 day 5): reject generation while the pipeline job is still running
    report = await generate_and_store_report(req.video_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No analytics found for {req.video_id}")
    return report

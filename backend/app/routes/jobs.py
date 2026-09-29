from fastapi import APIRouter

from app.db import fetch_jobs

router = APIRouter()


@router.get("/jobs")
def list_jobs(limit: int = 20):
    return {"jobs": fetch_jobs(limit)}

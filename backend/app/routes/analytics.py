from fastapi import APIRouter, HTTPException

from app.db import fetch_analies_placeholder

router = APIRouter()


@router.get("/analytics/{job_id}")
def get_analytics(job_id: str):
    raise HTTPException(status_code=501, detail="not implemented")

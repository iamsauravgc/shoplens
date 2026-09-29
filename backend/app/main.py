import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.jobs import resume_unfinished
from app.routes import analytics, heatmap, jobs, report, status, upload, zones

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # a --reload restart kills in-flight pipeline threads; pick them back up
    resume_unfinished()
    yield


app = FastAPI(title="ShopLens API", lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(status.router)
app.include_router(jobs.router)
app.include_router(analytics.router)
app.include_router(heatmap.router)
app.include_router(report.router)
app.include_router(zones.router)


@app.get("/health")
def health():
    return {"ok": True, "db": db.db_ok()}

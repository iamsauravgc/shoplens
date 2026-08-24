import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import analytics, heatmap, report, status, upload

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ShopLens API")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(status.router)
app.include_router(analytics.router)
app.include_router(heatmap.router)
app.include_router(report.router)


@app.get("/health")
def health():
    return {"ok": True, "redis": _ping_redis()}


def _ping_redis() -> bool:
    try:
        from app.config import get_redis

        get_redis().ping()
        return True
    except Exception:
        return False


@app.on_event("shutdown")
def close_redis():
    try:
        from app.config import get_redis

        get_redis().close()
    except Exception:
        pass

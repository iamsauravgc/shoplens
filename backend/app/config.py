import os
from dataclasses import dataclass

import redis


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str
    redis_url: str
    r2_endpoint: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    groq_api_key: str | None
    frontend_origin: str


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    return Settings(
        supabase_url=_required("SUPABASE_URL"),
        supabase_key=_required("SUPABASE_SERVICE_KEY"),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        r2_endpoint=_required("R2_ENDPOINT"),
        r2_access_key_id=_required("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        r2_bucket=os.environ.get("R2_BUCKET", "shoplens-videos"),
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        frontend_origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
    )


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


_redis = None


def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis

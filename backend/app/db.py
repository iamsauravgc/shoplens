from __future__ import annotations

import logging

from supabase import Client, create_client

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        s = get_settings()
        _client = create_client(s.supabase_url, s.supabase_key)
    return _client


def fetch_zones(store_id: str = "default") -> list[dict]:
    response = (
        get_client()
        .table("zones")
        .select("*")
        .eq("store_id", store_id)
        .order("created_at")
        .execute()
    )
    return response.data or []


def insert_video(record: dict) -> dict:
    response = get_client().table("videos").insert(record).execute()
    return response.data[0]


def update_video_status(video_id: str, status: str, error: str | None = None) -> None:
    payload: dict = {"status": status}
    if error is not None:
        payload["error"] = error
    get_client().table("videos").update(payload).eq("id", video_id).execute()


def upsert_analytics(record: dict) -> dict:
    response = get_client().table("analytics").upsert(record).execute()
    return response.data[0]


def fetch_analytics(video_id: str) -> dict | None:
    response = (
        get_client()
        .table("analytics")
        .select("*")
        .eq("video_id", video_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def insert_anomalies(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    response = get_client().table("anomalies").insert(rows).execute()
    return response.data or []


def fetch_anomalies(video_id: str) -> list[dict]:
    response = (
        get_client()
        .table("anomalies")
        .select("*")
        .eq("video_id", video_id)
        .order("frame")
        .execute()
    )
    return response.data or []


def insert_report(record: dict) -> dict:
    response = get_client().table("reports").upsert(record).execute()
    return response.data[0]


def fetch_report(video_id: str) -> dict | None:
    response = (
        get_client()
        .table("reports")
        .select("*")
        .eq("video_id", video_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None

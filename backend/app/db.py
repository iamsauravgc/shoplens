from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import get_settings

logger = logging.getLogger(__name__)

SCHEMA = """
create table if not exists videos (
    id text primary key,
    filename text,
    storage_key text,
    status text not null default 'queued',
    error text,
    created_at text not null
);

create table if not exists zones (
    id text primary key,
    store_id text not null default 'default',
    name text not null,
    polygon text not null,
    created_at text not null,
    unique (store_id, name)
);

create table if not exists analytics (
    id integer primary key autoincrement,
    video_id text not null unique,
    payload text not null,
    created_at text not null
);

create table if not exists anomalies (
    id integer primary key autoincrement,
    video_id text not null,
    anomaly_type text not null,
    zone_id text,
    frame integer,
    details text,
    created_at text not null
);

create table if not exists reports (
    id integer primary key autoincrement,
    video_id text not null unique,
    content text not null,
    model text,
    created_at text not null
);

create table if not exists jobs (
    job_id text primary key,
    step integer not null default 0,
    total_steps integer not null default 7,
    message text not null default '',
    state text not null default 'queued',
    updated_at text not null
);

create index if not exists idx_anomalies_video on anomalies(video_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    path: Path = get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("pragma journal_mode=WAL")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row(row: sqlite3.Row | None, json_fields: tuple[str, ...] = ()) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    for field in json_fields:
        if data.get(field):
            data[field] = json.loads(data[field])
    return data


def db_ok() -> bool:
    try:
        with _db() as conn:
            conn.execute("select 1")
        return True
    except Exception:
        logger.exception("database check failed")
        return False


# --- zones -----------------------------------------------------------------

def fetch_zones(store_id: str = "default") -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "select * from zones where store_id = ? order by created_at", (store_id,)
        ).fetchall()
    return [_row(r, ("polygon",)) for r in rows]  # type: ignore[misc]


def create_zone(name: str, polygon: list[dict], store_id: str = "default", zone_id: str | None = None) -> dict:
    zone_id = zone_id or str(uuid.uuid4())
    with _db() as conn:
        conn.execute(
            """insert into zones (id, store_id, name, polygon, created_at)
               values (?, ?, ?, ?, ?)
               on conflict (store_id, name) do update set polygon = excluded.polygon""",
            (zone_id, store_id, name, json.dumps(polygon), _now()),
        )
        row = conn.execute(
            "select * from zones where store_id = ? and name = ?", (store_id, name)
        ).fetchone()
    return _row(row, ("polygon",))  # type: ignore[return-value]


def delete_zone(zone_id: str) -> bool:
    with _db() as conn:
        cur = conn.execute("delete from zones where id = ?", (zone_id,))
        return cur.rowcount > 0


# --- videos ----------------------------------------------------------------

def insert_video(record: dict) -> dict:
    with _db() as conn:
        conn.execute(
            "insert into videos (id, filename, storage_key, status, created_at) values (?, ?, ?, ?, ?)",
            (record["id"], record.get("filename"), record.get("storage_key"), record.get("status", "queued"), _now()),
        )
        row = conn.execute("select * from videos where id = ?", (record["id"],)).fetchone()
    return _row(row)  # type: ignore[return-value]


def update_video_status(video_id: str, status: str, error: str | None = None) -> None:
    with _db() as conn:
        if error is not None:
            conn.execute("update videos set status = ?, error = ? where id = ?", (status, error, video_id))
        else:
            conn.execute("update videos set status = ? where id = ?", (status, video_id))


def fetch_video(video_id: str) -> dict | None:
    with _db() as conn:
        row = conn.execute("select * from videos where id = ?", (video_id,)).fetchone()
    return _row(row)


# --- analytics -------------------------------------------------------------

def upsert_analytics(record: dict) -> dict:
    with _db() as conn:
        conn.execute(
            """insert into analytics (video_id, payload, created_at)
               values (?, ?, ?)
               on conflict (video_id) do update set payload = excluded.payload""",
            (record["video_id"], json.dumps(record["payload"]), _now()),
        )
        row = conn.execute("select * from analytics where video_id = ?", (record["video_id"],)).fetchone()
    return _row(row, ("payload",))  # type: ignore[return-value]


def fetch_analytics(video_id: str) -> dict | None:
    with _db() as conn:
        row = conn.execute("select * from analytics where video_id = ?", (video_id,)).fetchone()
    return _row(row, ("payload",))


# --- anomalies -------------------------------------------------------------

def insert_anomalies(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    now = _now()
    with _db() as conn:
        # replace: analytics are a per-video snapshot, so re-runs (e.g. resume
        # after a --reload restart) must not duplicate rows
        conn.execute("delete from anomalies where video_id = ?", (rows[0]["video_id"],))
        for r in rows:
            conn.execute(
                "insert into anomalies (video_id, anomaly_type, zone_id, frame, details, created_at) values (?, ?, ?, ?, ?, ?)",
                (
                    r["video_id"],
                    r["anomaly_type"],
                    r.get("zone_id"),
                    r.get("frame"),
                    json.dumps(r.get("details") or {}),
                    now,
                ),
            )
        fetched = conn.execute(
            "select * from anomalies where video_id = ? order by id", (rows[0]["video_id"],)
        ).fetchall()
    return [_row(r, ("details",)) for r in fetched]  # type: ignore[misc]


def fetch_anomalies(video_id: str) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "select * from anomalies where video_id = ? order by frame, id", (video_id,)
        ).fetchall()
    return [_row(r, ("details",)) for r in rows]  # type: ignore[misc]


# --- reports ---------------------------------------------------------------

def insert_report(record: dict) -> dict:
    with _db() as conn:
        conn.execute(
            """insert into reports (video_id, content, model, created_at)
               values (?, ?, ?, ?)
               on conflict (video_id) do update set content = excluded.content, model = excluded.model""",
            (record["video_id"], record["content"], record.get("model"), _now()),
        )
        row = conn.execute("select * from reports where video_id = ?", (record["video_id"],)).fetchone()
    return _row(row)  # type: ignore[return-value]


def fetch_report(video_id: str) -> dict | None:
    with _db() as conn:
        row = conn.execute("select * from reports where video_id = ?", (video_id,)).fetchone()
    return _row(row)


# --- job progress ----------------------------------------------------------

def set_job_progress(job_id: str, step: int, total_steps: int, message: str, state: str = "processing") -> None:
    with _db() as conn:
        conn.execute(
            """insert into jobs (job_id, step, total_steps, message, state, updated_at)
               values (?, ?, ?, ?, ?, ?)
               on conflict (job_id) do update set
                 step = excluded.step, total_steps = excluded.total_steps,
                 message = excluded.message, state = excluded.state, updated_at = excluded.updated_at""",
            (job_id, step, total_steps, message, state, _now()),
        )


def get_job_progress(job_id: str) -> dict | None:
    with _db() as conn:
        row = conn.execute("select * from jobs where job_id = ?", (job_id,)).fetchone()
    return _row(row)


def fetch_unfinished_jobs() -> list[dict]:
    """Jobs left in queued/processing by a crashed or reloaded server process."""
    with _db() as conn:
        rows = conn.execute(
            """select j.job_id, v.storage_key
               from jobs j join videos v on v.id = j.job_id
               where j.state in ('queued', 'processing')
               order by j.updated_at"""
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_jobs(limit: int = 20) -> list[dict]:
    """Past analyses, newest first, so the dashboard can reopen finished jobs."""
    with _db() as conn:
        rows = conn.execute(
            """select j.job_id, j.state, j.message, j.updated_at, v.filename,
                      (a.video_id is not null) as has_analytics,
                      (r.video_id is not null) as has_report,
                      (select count(*) from anomalies n where n.video_id = j.job_id) as anomaly_count
               from jobs j
               join videos v on v.id = j.job_id
               left join analytics a on a.video_id = j.job_id
               left join reports r on r.video_id = j.job_id
               order by j.updated_at desc
               limit ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]

from __future__ import annotations

import logging
import threading

from app.db import fetch_unfinished_jobs, set_job_progress
from workers.pipeline import TOTAL_STEPS, process_video

logger = logging.getLogger(__name__)


def enqueue_processing(job_id: str, storage_key: str, store_id: str = "default") -> None:
    set_job_progress(job_id, 0, TOTAL_STEPS, "Queued", state="queued")
    thread = threading.Thread(
        target=_run,
        args=(job_id, storage_key, store_id),
        name=f"pipeline-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    logger.info("enqueued %s", job_id)


def resume_unfinished() -> int:
    """Re-enqueue jobs whose worker thread died with the previous process.

    uvicorn --reload (WatchFiles) restarts the process whenever a module
    changes; without this, an in-flight pipeline would sit at its last DB
    checkpoint forever. Re-runs are safe: analytics upsert, anomalies replace,
    heatmaps overwrite.
    """
    resumed = 0
    for job in fetch_unfinished_jobs():
        logger.info("resuming unfinished job %s", job["job_id"])
        enqueue_processing(job["job_id"], job["storage_key"])
        resumed += 1
    return resumed


def _run(job_id: str, storage_key: str, store_id: str) -> None:
    try:
        process_video(job_id, storage_key, store_id)
    except Exception:
        # process_video records its own failure state; this stops the thread from dying silently
        logger.exception("pipeline crashed for %s", job_id)

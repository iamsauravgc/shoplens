import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from rq import Queue

from app.config import get_redis
from app.db import insert_video
from app.storage import upload_file
from workers.pipeline import PROCESS_VIDEO_TIMEOUT, QUEUE_NAME, process_video

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
MAX_UPLOAD_MB = 200


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    job_id = str(uuid.uuid4())
    tmp_path = Path(tempfile.gettempdir()) / f"shoplens_{job_id}{suffix}"

    size_bytes = 0
    with tmp_path.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size_bytes += len(chunk)
            if size_bytes > MAX_UPLOAD_MB * 1024 * 1024:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Video larger than {MAX_UPLOAD_MB}MB")
            out.write(chunk)

    storage_key = f"videos/{job_id}{suffix}"
    upload_file(tmp_path, storage_key, content_type=file.content_type or "video/mp4")

    video = insert_video({"id": job_id, "filename": file.filename, "storage_key": storage_key, "status": "queued"})

    queue = Queue(QUEUE_NAME, connection=get_redis())
    queue.enqueue(process_video, job_id, storage_key, job_timeout=PROCESS_VIDEO_TIMEOUT)

    logger.info("queued %s (%d bytes)", job_id, size_bytes)
    return {"job_id": job_id, "status": "queued", "video": video}

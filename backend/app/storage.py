from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.client import Config

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_r2_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.r2_endpoint,
        aws_access_key_id=s.r2_access_key_id,
        aws_secret_access_key=s.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_file(local_path: str | Path, key: str, content_type: str = "video/mp4") -> str:
    client = get_r2_client()
    client.upload_file(
        str(local_path),
        get_settings().r2_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    logger.info("uploaded %s to %s", local_path, key)
    return key


def download_to(key: str, dest_path: str | Path) -> Path:
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    get_r2_client().download_file(get_settings().r2_bucket, key, str(dest_path))
    return dest_path


def read_bytes(key: str) -> bytes:
    response = get_r2_client().get_object(Bucket=get_settings().r2_bucket, Key=key)
    return response["Body"].read()


def object_exists(key: str) -> bool:
    try:
        get_r2_client().head_object(Bucket=get_settings().r2_bucket, Key=key)
        return True
    except Exception:
        return False

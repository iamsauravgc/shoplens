from __future__ import annotations

import logging
import shutil
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _root() -> Path:
    root = get_settings().storage_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve(key: str) -> Path:
    path = (_root() / key).resolve()
    if not path.is_relative_to(_root()):
        raise ValueError(f"Invalid storage key: {key}")
    return path


def upload_file(local_path: str | Path, key: str, content_type: str = "video/mp4") -> str:
    dest = _resolve(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if Path(local_path).resolve() != dest:
        shutil.copy2(local_path, dest)
    logger.info("stored %s as %s", local_path, key)
    return key


def download_to(key: str, dest_path: str | Path) -> Path:
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_resolve(key), dest_path)
    return dest_path


def read_bytes(key: str) -> bytes:
    return _resolve(key).read_bytes()


def object_exists(key: str) -> bool:
    return _resolve(key).exists()

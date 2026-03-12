from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from backend.app.core.config import EXPORT_DIR, UPLOAD_DIR, ensure_directories


ensure_directories()


def compute_file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


async def save_upload(upload: UploadFile, category: str) -> Path:
    extension = Path(upload.filename or "").suffix
    target_dir = UPLOAD_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid.uuid4().hex}{extension}"
    with target_path.open("wb") as file_handle:
        shutil.copyfileobj(upload.file, file_handle)
    await upload.close()
    return target_path


def make_export_path(base_name: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(base_name).stem
    return EXPORT_DIR / f"{safe_name}_result.xlsx"

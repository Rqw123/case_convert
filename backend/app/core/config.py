from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "app.sqlite3"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"

API_PREFIX = "/api"
DEFAULT_HOST = os.getenv("APP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("APP_PORT", "8000"))


def ensure_directories() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR, DB_DIR):
        path.mkdir(parents=True, exist_ok=True)

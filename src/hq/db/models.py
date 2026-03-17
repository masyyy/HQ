import sqlite_utils

from hq.config import HQ_DIR

DB_PATH = HQ_DIR / "hq.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    module     TEXT NOT NULL CHECK(module IN ('crm', 'board')),
    stage      TEXT NOT NULL,
    assignee   TEXT,
    description TEXT,
    contacts   TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);
"""


_db: sqlite_utils.Database | None = None


def get_db() -> sqlite_utils.Database:
    global _db
    if _db is not None:
        return _db
    HQ_DIR.mkdir(parents=True, exist_ok=True)
    _db = sqlite_utils.Database(DB_PATH)
    _db.execute(SCHEMA_SQL)
    return _db


def ensure_db() -> None:
    get_db()

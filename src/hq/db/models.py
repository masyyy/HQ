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
    position   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);
"""


_db: sqlite_utils.Database | None = None


def _migrate(db: sqlite_utils.Database) -> None:
    """Run forward-only migrations on existing databases."""
    columns = {col.name for col in db["entities"].columns}

    if "position" not in columns:
        db.execute("ALTER TABLE entities ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
        # Backfill: assign sequential positions per (module, stage), ordered by created_at then id
        db.execute("""
            UPDATE entities SET position = (
                SELECT COUNT(*)
                FROM entities AS e2
                WHERE e2.module = entities.module
                  AND e2.stage = entities.stage
                  AND e2.deleted_at IS NULL
                  AND (e2.created_at < entities.created_at
                       OR (e2.created_at = entities.created_at AND e2.id < entities.id))
            )
            WHERE deleted_at IS NULL
        """)


def get_db() -> sqlite_utils.Database:
    global _db
    if _db is not None:
        return _db
    HQ_DIR.mkdir(parents=True, exist_ok=True)
    _db = sqlite_utils.Database(DB_PATH)
    _db.execute(SCHEMA_SQL)
    _migrate(_db)
    return _db


def ensure_db() -> None:
    get_db()

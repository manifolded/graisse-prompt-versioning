"""Database: schema, connection, and queries."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import get_db_path


class DBError(Exception):
    """Database error."""


SUB_PROMPTS_SCHEMA = """
CREATE TABLE sub_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    parent_id INTEGER,
    version TEXT NOT NULL,
    contents TEXT NOT NULL,
    commit_message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(contents)
);
CREATE UNIQUE INDEX idx_sub_prompts_contents ON sub_prompts(contents);
"""

MASTER_PROMPTS_SCHEMA = """
CREATE TABLE master_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    version TEXT NOT NULL,
    contents TEXT NOT NULL,
    is_current INTEGER NOT NULL,
    commit_message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(contents)
);
CREATE UNIQUE INDEX idx_master_prompts_contents ON master_prompts(contents);
CREATE UNIQUE INDEX idx_master_prompts_current ON master_prompts(id) WHERE is_current = 1;
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the database. Creates file if it does not exist."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create tables if both are absent. If either exists, raise ConfigError.
    """
    has_sub = table_exists(conn, "sub_prompts")
    has_master = table_exists(conn, "master_prompts")
    if has_sub or has_master:
        raise DBError(
            "Cannot migrate: sub_prompts or master_prompts table already exists"
        )
    with conn:
        conn.executescript(SUB_PROMPTS_SCHEMA)
        conn.executescript(MASTER_PROMPTS_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def insert_sub_prompt(
    conn: sqlite3.Connection,
    *,
    type: str,
    parent_id: int | None,
    version: str,
    contents: str,
    commit_message: str,
) -> int:
    """Insert a sub_prompt row. Returns the new id."""
    cur = conn.execute(
        """
        INSERT INTO sub_prompts (type, parent_id, version, contents, commit_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (type, parent_id, version, contents, commit_message, _now()),
    )
    return cur.lastrowid


def get_sub_prompt_by_contents(conn: sqlite3.Connection, contents: str) -> sqlite3.Row | None:
    """Get sub_prompt by contents, or None."""
    cur = conn.execute("SELECT * FROM sub_prompts WHERE contents = ?", (contents,))
    return cur.fetchone()


def get_sub_prompt_by_id(conn: sqlite3.Connection, id: int) -> sqlite3.Row | None:
    """Get sub_prompt by id."""
    cur = conn.execute("SELECT * FROM sub_prompts WHERE id = ?", (id,))
    return cur.fetchone()


def get_current_master(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Get the current master prompt (is_current=1)."""
    cur = conn.execute(
        "SELECT * FROM master_prompts WHERE is_current = 1"
    )
    return cur.fetchone()


def get_master_by_id(conn: sqlite3.Connection, id: int) -> sqlite3.Row | None:
    """Get master prompt by id."""
    cur = conn.execute("SELECT * FROM master_prompts WHERE id = ?", (id,))
    return cur.fetchone()


def get_previous_master(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Get the parent of the current master (the one to revert to on uncommit)."""
    current = get_current_master(conn)
    if not current or current["parent_id"] is None:
        return None
    return get_master_by_id(conn, current["parent_id"])


def get_sub_prompts_by_ids(
    conn: sqlite3.Connection, ids: list[int]
) -> list[sqlite3.Row]:
    """Get sub_prompts by ids, in the order of ids."""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    cur = conn.execute(
        f"SELECT * FROM sub_prompts WHERE id IN ({placeholders})",
        ids,
    )
    by_id = {row["id"]: row for row in cur.fetchall()}
    return [by_id[i] for i in ids if i in by_id]


def master_contents_to_ids(contents: str) -> list[int]:
    """Parse master prompt contents (JSON list) to sub_prompt ids."""
    return json.loads(contents)


def ids_to_master_contents(ids: list[int]) -> str:
    """Serialize sub_prompt ids to JSON for master prompt contents."""
    return json.dumps(ids)


def insert_master_prompt(
    conn: sqlite3.Connection,
    *,
    parent_id: int | None,
    version: str,
    contents: str,
    is_current: int,
    commit_message: str,
) -> int:
    """Insert a master_prompt row. Returns the new id."""
    cur = conn.execute(
        """
        INSERT INTO master_prompts (parent_id, version, contents, is_current, commit_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (parent_id, version, contents, is_current, commit_message, _now()),
    )
    return cur.lastrowid


def clear_current_master(conn: sqlite3.Connection) -> None:
    """Set is_current=0 for the row that has is_current=1."""
    conn.execute("UPDATE master_prompts SET is_current = 0 WHERE is_current = 1")


def set_current_master(conn: sqlite3.Connection, master_id: int) -> None:
    """Set the specified master prompt as current (is_current=1). Clears current first."""
    conn.execute("UPDATE master_prompts SET is_current = 0 WHERE is_current = 1")
    conn.execute("UPDATE master_prompts SET is_current = 1 WHERE id = ?", (master_id,))


def delete_master_prompt(conn: sqlite3.Connection, master_id: int) -> None:
    """Delete a master prompt row."""
    conn.execute("DELETE FROM master_prompts WHERE id = ?", (master_id,))


def delete_sub_prompts(conn: sqlite3.Connection, ids: list[int]) -> None:
    """Delete sub_prompt rows by id."""
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM sub_prompts WHERE id IN ({placeholders})", ids)

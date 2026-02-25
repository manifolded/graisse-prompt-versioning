"""Shared test utilities."""

import sqlite3


def db_state(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """Return (sub_prompts, master_prompts) as lists of dicts, ordered by id."""
    sub_rows = conn.execute(
        "SELECT id, type, parent_id, version, contents, commit_message, created_at "
        "FROM sub_prompts ORDER BY id"
    ).fetchall()
    master_rows = conn.execute(
        "SELECT id, parent_id, version, contents, is_current, commit_message, created_at "
        "FROM master_prompts ORDER BY id"
    ).fetchall()
    sub_prompts = [dict(row) for row in sub_rows]
    master_prompts = [dict(row) for row in master_rows]
    return (sub_prompts, master_prompts)

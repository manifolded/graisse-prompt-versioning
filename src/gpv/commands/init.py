"""gpv init: create database and schema."""

from pathlib import Path

from ..config import get_db_path
from ..db import connect, init_schema


def run_init(cwd: Path | None = None) -> None:
    """
    1. Resolve CWD, look for .gpv in CWD
    2. If .gpv missing -> error
    3. Read DB path from .gpv; if empty/invalid -> error
    4. Create DB file if it does not exist
    5. If both sub_prompts and master_prompts are absent -> in a transaction, create both tables and indexes.
       If either table is already present -> error.
    """
    db_path = get_db_path(cwd)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        init_schema(conn)
    finally:
        conn.close()

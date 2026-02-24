"""gpv info: print details of current master prompt."""

from pathlib import Path

from ..config import get_db_path
from ..db import (
    connect,
    get_current_master,
    get_master_by_id,
    get_sub_prompts_by_ids,
    master_contents_to_ids,
)


class InfoError(Exception):
    """Info error."""


def run_info(master_pk: int | None = None, cwd: Path | None = None) -> None:
    """Print details of current master prompt (or specified by pk)."""
    db_path = get_db_path(cwd)
    conn = connect(db_path)

    if master_pk is not None:
        master = get_master_by_id(conn, master_pk)
        if not master:
            raise InfoError(f"Master prompt {master_pk} not found")
    else:
        master = get_current_master(conn)
        if not master:
            raise InfoError("No current master prompt")

    ids = master_contents_to_ids(master["contents"])
    subs = get_sub_prompts_by_ids(conn, ids)

    print(f"id: {master['id']}")
    print(f"version: {master['version']}")
    print(f"commit_message: {master['commit_message']}")
    print(f"created_at: {master['created_at']}")
    print(f"is_current: {master['is_current']}")
    print("sub_prompts:")
    for sub in subs:
        print(f"  - id={sub['id']} type={sub['type']} version={sub['version']}")

    conn.close()

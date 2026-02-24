"""gpv extract: create .j2 files from current master sub-prompts."""

from pathlib import Path

from ..config import get_db_path
from ..db import (
    connect,
    get_current_master,
    get_master_by_id,
    get_sub_prompts_by_ids,
    master_contents_to_ids,
)

from .commit import type_to_filename


class ExtractError(Exception):
    """Extract error."""


def run_extract(master_pk: int | None = None, cwd: Path | None = None) -> None:
    """
    Create files in CWD, one per sub-prompt in the current master.
    Filenames from type (reverse of gpv commit).
    Requires confirmation if any target file exists.
    """
    db_path = get_db_path(cwd)
    cwd = cwd or Path.cwd()
    conn = connect(db_path)

    if master_pk is not None:
        master = get_master_by_id(conn, master_pk)
        if not master:
            raise ExtractError(f"Master prompt {master_pk} not found")
    else:
        master = get_current_master(conn)
        if not master:
            raise ExtractError("No current master prompt")

    ids = master_contents_to_ids(master["contents"])
    subs = get_sub_prompts_by_ids(conn, ids)

    total = len(subs)
    existing = []
    for i, sub in enumerate(subs):
        fname = type_to_filename(sub["type"], index=i, total=total)
        if (cwd / fname).exists():
            existing.append(fname)

    if existing:
        print(f"The following files would be overwritten: {', '.join(existing)}")
        response = input("Proceed? [y/N]: ").strip().lower()
        if response != "y":
            print("Aborted.")
            conn.close()
            return

    for i, sub in enumerate(subs):
        fname = type_to_filename(sub["type"], index=i, total=total)
        (cwd / fname).write_text(sub["contents"])

    conn.close()

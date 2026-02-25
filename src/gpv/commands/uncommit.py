"""gpv uncommit: revert to the previous master prompt."""

from pathlib import Path

from ..config import get_db_path
from ..db import (
    connect,
    delete_master_prompt,
    delete_sub_prompts,
    get_current_master,
    get_previous_master,
    master_contents_to_ids,
    set_current_master,
)


class UncommitError(Exception):
    """Uncommit error."""


def run_uncommit(cwd: Path | None = None, confirm: bool = True) -> None:
    """
    Revert to the previous master prompt (parent of current).
    Deletes current master, sets parent as current, deletes sub-prompts
    inserted in the last commit.
    """
    db_path = get_db_path(cwd)
    conn = connect(db_path)

    current = get_current_master(conn)
    if not current:
        raise UncommitError("No current master prompt")

    previous = get_previous_master(conn)
    if not previous:
        raise UncommitError("No previous master to revert to")

    if confirm:
        print(f"Uncommit will revert from master {current['id']} to {previous['id']}.")
        print("This is irreversible.")
        response = input("Proceed? [y/N]: ").strip().lower()
        if response != "y":
            print("Aborted.")
            return

    current_ids = set(master_contents_to_ids(current["contents"]))
    previous_ids = set(master_contents_to_ids(previous["contents"]))
    to_delete = list(current_ids - previous_ids)

    with conn:
        delete_master_prompt(conn, current["id"])
        set_current_master(conn, previous["id"])
        delete_sub_prompts(conn, to_delete)

    conn.close()

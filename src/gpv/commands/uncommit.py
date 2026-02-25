"""gpv uncommit: revert to the previous master prompt."""

from pathlib import Path

from ..config import get_db_path
from ..db import (
    connect,
    delete_master_prompt,
    delete_sub_prompts,
    get_current_master,
    get_previous_master,
    get_sub_prompts_by_ids,
    master_contents_to_ids,
    set_current_master,
)
from ..versioning import version_gt


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

    current_ids = master_contents_to_ids(current["contents"])
    previous_ids = master_contents_to_ids(previous["contents"])
    current_subs = get_sub_prompts_by_ids(conn, current_ids)
    previous_subs = get_sub_prompts_by_ids(conn, previous_ids)
    current_by_type = {row["type"]: (row["id"], row["version"]) for row in current_subs}
    previous_by_type = {row["type"]: (row["id"], row["version"]) for row in previous_subs}

    to_delete: list[int] = []
    for sub_type, (sub_id, sub_version) in current_by_type.items():
        prev = previous_by_type.get(sub_type)
        if prev is None:
            to_delete.append(sub_id)
        else:
            _, prev_version = prev
            if version_gt(sub_version, prev_version):
                to_delete.append(sub_id)

    with conn:
        delete_master_prompt(conn, current["id"])
        set_current_master(conn, previous["id"])
        delete_sub_prompts(conn, to_delete)

    conn.close()

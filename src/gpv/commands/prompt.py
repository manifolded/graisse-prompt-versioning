"""gpv prompt: print concatenated sub-prompts with type prefix."""

from pathlib import Path

from ..config import get_db_path
from ..db import (
    connect,
    get_current_master,
    get_master_by_id,
    get_sub_prompts_by_ids,
    master_contents_to_ids,
)


class PromptError(Exception):
    """Prompt error."""


def run_prompt(master_pk: int | None = None, cwd: Path | None = None) -> None:
    """Print concatenated contents of sub-prompts, each preceded by its type."""
    db_path = get_db_path(cwd)
    conn = connect(db_path)

    if master_pk is not None:
        master = get_master_by_id(conn, master_pk)
        if not master:
            raise PromptError(f"Master prompt {master_pk} not found")
    else:
        master = get_current_master(conn)
        if not master:
            raise PromptError("No current master prompt")

    ids = master_contents_to_ids(master["contents"])
    subs = get_sub_prompts_by_ids(conn, ids)

    for sub in subs:
        print(f"[{sub['type']}]")
        print(sub["contents"])
        print()

    conn.close()

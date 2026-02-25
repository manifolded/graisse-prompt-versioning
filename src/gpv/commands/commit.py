"""gpv commit: commit sub-prompts and create new master prompt."""

from pathlib import Path

from jinja2 import Environment, TemplateSyntaxError

from ..config import get_db_path
from ..db import (
    clear_current_master,
    connect,
    get_current_master,
    get_sub_prompt_by_contents,
    get_sub_prompt_by_id,
    get_sub_prompts_by_ids,
    ids_to_master_contents,
    insert_master_prompt,
    insert_sub_prompt,
    master_contents_to_ids,
)
from ..versioning import branch_version, derive_master_version, increment_version


class CommitError(Exception):
    """Commit error."""


class DuplicateTypeInCommitError(CommitError):
    """Raised when the commit would add multiple files with the same sub-prompt type."""


class DuplicateTypeInCurrentError(CommitError):
    """Raised when the current master already has duplicate sub-prompt types."""


def extract_type_from_filename(filename: str) -> str:
    """
    Extract type from filename *_<type>.j2 -> extract between first underscore and .j2
    E.g. a_intro.j2 -> intro, a_intro_section.j2 -> intro_section
    """
    if not filename.endswith(".j2"):
        raise ValueError(f"Filename must end with .j2: {filename}")
    name = filename[:-3]
    if "_" not in name:
        raise ValueError(f"Filename must contain underscore before .j2: {filename}")
    return name.split("_", 1)[1]


def _index_to_prefix(index: int, total: int) -> str:
    """
    Convert 0-based index to zero-padded numeric prefix for filename ordering.
    Uses 2+ digits: 01, 02, ..., 99, 100, ...
    """
    width = max(2, len(str(total)))
    return str(index + 1).zfill(width)


def type_to_filename(type_name: str, index: int = 0, total: int = 1) -> str:
    """
    Reverse of extract_type_from_filename: type + position -> {prefix}_{type}.j2.
    The prefix is a zero-padded number (01, 02, ...) from the sub-prompt's order in the master.
    """
    return f"{_index_to_prefix(index, total)}_{type_name}.j2"


def validate_jinja2(contents: str) -> None:
    """Validate contents as jinja2. Raises TemplateSyntaxError if invalid."""
    Environment().from_string(contents)


def run_commit(
    message: str,
    paths: list[Path] | None = None,
    branch_specs: list[tuple[int, Path]] | None = None,
    no_validate: bool = False,
    cwd: Path | None = None,
) -> None:
    """
    Commit sub-prompts and create a new master prompt (making it current).
    Inserts or reuses sub-prompt rows, then inserts a new master_prompts row with
    is_current=1 and clears is_current on the previous master.
    If paths is None, scan CWD for *.j2.
    branch_specs: list of (parent_pk, path) for forced branch versioning.
    """
    if not message:
        raise CommitError("Commit message is required (-m)")
    db_path = get_db_path(cwd)
    cwd = cwd or Path.cwd()

    if paths is None:
        # glob() returns files in arbitrary order (filesystem-dependent); sort by name
        # so sub-prompts follow filename prefix order (e.g. 01_intro, 02_body).
        paths = sorted(cwd.glob("*.j2"), key=lambda p: p.name)
    else:
        for p in paths:
            if not p.exists():
                raise CommitError(f"Path does not exist: {p}")
        # Sort by name for consistent sub-prompt order.
        paths = sorted([p for p in paths if p.name.endswith(".j2")], key=lambda p: p.name)

    branch_by_path = {}
    if branch_specs:
        for parent_pk, path in branch_specs:
            path = path.resolve() if not path.is_absolute() else path
            branch_by_path[path] = parent_pk

    files_data: list[tuple[Path, str, str]] = []
    for p in paths:
        p = p.resolve() if not p.is_absolute() else p
        contents = p.read_text()
        type_name = extract_type_from_filename(p.name)
        if not no_validate:
            try:
                validate_jinja2(contents)
            except TemplateSyntaxError as e:
                raise CommitError(f"Invalid jinja2 in {p}: {e}") from e
        files_data.append((p, contents, type_name))

    if not files_data:
        print("Nothing to commit. No .j2 files or no changes.")
        return

    # Detect duplicate types in commit (multiple files with same type); raise if any.
    seen: dict[str, list[str]] = {}
    for path, _, type_name in files_data:
        seen.setdefault(type_name, []).append(str(path.name))
    duplicates = {t: paths for t, paths in seen.items() if len(paths) > 1}
    if duplicates:
        dup_desc = "; ".join(f"{t} ({', '.join(p)})" for t, p in duplicates.items())
        raise DuplicateTypeInCommitError(
            f"Multiple files with same sub-prompt type in commit: {dup_desc}"
        )

    conn = connect(db_path)
    try:
        current = get_current_master(conn)
        current_ids = master_contents_to_ids(current["contents"]) if current else []
        current_subs = get_sub_prompts_by_ids(conn, current_ids) if current_ids else []
        current_by_type = {row["type"]: row["version"] for row in current_subs}

        type_to_id: dict[str, int] = {}
        id_to_version: dict[int, str] = {}
        id_to_type: dict[int, str] = {}
        inserted_any = False

        for path, contents, type_name in files_data:
            existing = get_sub_prompt_by_contents(conn, contents)
            if existing:
                type_to_id[type_name] = existing["id"]
                id_to_version[existing["id"]] = existing["version"]
                id_to_type[existing["id"]] = existing["type"]
                continue

            parent_id = None
            parent_version = None
            if current:
                for sub in current_subs:
                    if sub["type"] == type_name:
                        parent_id = sub["id"]
                        parent_version = sub["version"]
                        break

            if path in branch_by_path:
                parent_pk = branch_by_path[path]
                parent_row = get_sub_prompt_by_id(conn, parent_pk)
                if not parent_row:
                    raise CommitError(f"Parent sub-prompt {parent_pk} not found")
                if parent_row["type"] != type_name:
                    raise CommitError(
                        f"Parent {parent_pk} has type {parent_row['type']}, expected {type_name}"
                    )
                parent_id = parent_pk
                parent_version = parent_row["version"]
                version = branch_version(parent_version)
            else:
                version = increment_version(parent_version)

            new_id = insert_sub_prompt(
                conn,
                type=type_name,
                parent_id=parent_id,
                version=version,
                contents=contents,
                commit_message=message,
            )
            conn.commit()
            type_to_id[type_name] = new_id
            id_to_version[new_id] = version
            id_to_type[new_id] = type_name
            inserted_any = True

        current_ids = master_contents_to_ids(current["contents"]) if current else []
        types_in_commit = {type_name for _, _, type_name in files_data}
        current_type_order = [type_name for _, _, type_name in files_data]
        for row in current_subs:
            if row["type"] not in types_in_commit:
                if row["type"] in current_type_order:
                    raise DuplicateTypeInCurrentError(
                        f"Current master has duplicate sub-prompt type '{row['type']}'"
                    )
                current_type_order.append(row["type"])

        new_ids: list[int] = []
        for t in current_type_order:
            if t in type_to_id:
                new_ids.append(type_to_id[t])
            elif current:
                for sub in current_subs:
                    if sub["type"] == t:
                        sid = sub["id"]
                        new_ids.append(sid)
                        id_to_version[sid] = sub["version"]
                        id_to_type[sid] = sub["type"]
                        break

        if not new_ids:
            print("Nothing to commit. No changes detected.")
            return

        if not inserted_any and current and new_ids == current_ids:
            print("Nothing to commit. No changes detected.")
            return

        current_version = current["version"] if current else None
        new_master_version = derive_master_version(
            current_version,
            current_by_type,
            new_ids,
            id_to_version,
            id_to_type,
        )

        new_contents = ids_to_master_contents(new_ids)

        with conn:
            if current:
                clear_current_master(conn)
            insert_master_prompt(
                conn,
                parent_id=current["id"] if current else None,
                version=new_master_version,
                contents=new_contents,
                is_current=1,
                commit_message=message,
            )
    finally:
        conn.close()


def run_commit_paths(
    message: str,
    paths: list[Path],
    no_validate: bool = False,
    cwd: Path | None = None,
) -> None:
    """
    Commit only the listed .j2 files (instead of scanning CWD).
    Paths may be relative to CWD or absolute. Each path must exist and end with .j2.
    """
    run_commit(message=message, paths=paths, no_validate=no_validate, cwd=cwd)


def run_commit_branch(
    message: str,
    branch_specs: list[tuple[int, Path]],
    no_validate: bool = False,
    cwd: Path | None = None,
) -> None:
    """
    Commit with forced branch versioning. Each (parent_pk, path) pair specifies
    a sub-prompt file to commit, branching from the given parent instead of
    simple increment. May be repeated to branch multiple sub-prompts in one call.
    """
    paths = [p for _, p in branch_specs]
    run_commit(
        message=message,
        paths=paths,
        branch_specs=branch_specs,
        no_validate=no_validate,
        cwd=cwd,
    )

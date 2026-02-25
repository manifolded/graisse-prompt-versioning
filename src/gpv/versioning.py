"""Version number logic for sub-prompts and master prompts."""


def increment_version(parent_version: str | None) -> str:
    """
    Simple increment: increment the last segment.
    Parent "4.3" -> "4.4"
    Parent None (first of type) -> "1"
    """
    if parent_version is None:
        return "1"
    parts = parent_version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def branch_version(parent_version: str) -> str:
    """
    Branch: append .1 to parent.
    Parent "4.3" -> "4.3.1"
    """
    return f"{parent_version}.1"


def version_gt(new_version: str, old_version: str) -> bool:
    """
    True if new_version is later than old_version.
    Compares segment-by-segment numerically (e.g. 4.4 > 4.3, 4.3.1 > 4.3).
    """
    parts_new = [int(x) for x in new_version.split(".")]
    parts_old = [int(x) for x in old_version.split(".")]
    for i in range(max(len(parts_new), len(parts_old))):
        vn = parts_new[i] if i < len(parts_new) else 0
        vo = parts_old[i] if i < len(parts_old) else 0
        if vn > vo:
            return True
        if vn < vo:
            return False
    return False


def version_segment_count(version: str) -> int:
    """Number of segments in a version string (e.g. '4.3.1' -> 3)."""
    return len(version.split("."))


def is_branched(new_version: str, old_version: str) -> bool:
    """
    True if new_version has more segments than old_version.
    E.g. new="4.3.1", old="4.3" -> True
    """
    return version_segment_count(new_version) > version_segment_count(old_version)


def derive_master_version(
    current_master_version: str | None,
    current_by_type: dict[str, str],
    new_sub_ids: list[int],
    new_id_to_version: dict[int, str],
    new_id_to_type: dict[int, str],
) -> str:
    """
    Derive the new master prompt version.
    - If current master is None (empty table), return "1"
    - If any sub-prompt in new master is branched vs current (same type, more segments), master version is branched
    - Otherwise, simple increment

    current_by_type: type -> version for sub-prompts in current master
    new_id_to_version, new_id_to_type: mappings for sub-prompts in new master
    """
    if current_master_version is None:
        return "1"
    any_branched = False
    for new_id in new_sub_ids:
        new_ver = new_id_to_version.get(new_id)
        sub_type = new_id_to_type.get(new_id)
        old_ver = current_by_type.get(sub_type) if sub_type else None
        if new_ver and old_ver and is_branched(new_ver, old_ver):
            any_branched = True
            break
    if any_branched:
        return branch_version(current_master_version)
    return increment_version(current_master_version)

"""Tests for commit type extraction and validation."""

import pytest

from gpv.commands.commit import (
    DuplicateTypeInCommitError,
    PartialCommitAddsNewTypeError,
    PartialCommitMissingCwdFileError,
    extract_type_from_filename,
    run_commit,
    run_commit_paths,
)
from gpv.commands.prompt import run_prompt
from gpv.config import get_db_path
from gpv.db import connect


def test_extract_type() -> None:
    assert extract_type_from_filename("a_intro.j2") == "intro"
    assert extract_type_from_filename("a_intro_section.j2") == "intro_section"
    assert extract_type_from_filename("01_intro.j2") == "intro"
    assert extract_type_from_filename("01a_intro.j2") == "intro"


def test_extract_type_invalid() -> None:
    with pytest.raises(ValueError):
        extract_type_from_filename("intro.js")
        extract_type_from_filename("a_intro")


def test_commit_rejects_duplicate_types(tmp_path, monkeypatch) -> None:
    """Commit raises when multiple files have the same sub-prompt type."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_intro.j2").write_text("First intro")
    (tmp_path / "02_intro.j2").write_text("Second intro")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    with pytest.raises(DuplicateTypeInCommitError) as exc_info:
        run_commit(message="Test", cwd=tmp_path)
    assert "intro" in str(exc_info.value)


def test_commit_with_inconsistent_order_prefixes(tmp_path, monkeypatch, capsys) -> None:
    """Full commit with 1_intro.j2 and 02_body.j2; order follows filename sort."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "1_intro.j2").write_text("Intro")
    (tmp_path / "02_body.j2").write_text("Body")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit(message="Full commit", cwd=tmp_path)

    run_prompt(cwd=tmp_path)
    out = capsys.readouterr().out
    types = [line.strip() for line in out.splitlines() if line.startswith("[")]
    assert types == ["[body]", "[intro]"]


def test_commit_allows_full_commit_with_new_types(tmp_path, monkeypatch, capsys) -> None:
    """Full commit can add new types; order follows filename prefixes."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_a_header.j2").write_text("Header")
    (tmp_path / "02_b_consideration.j2").write_text("Consideration")
    (tmp_path / "03_c_instruction.j2").write_text("Instruction")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit_paths(
        message="First",
        paths=[tmp_path / "01_a_header.j2"],
        cwd=tmp_path,
    )

    run_commit(message="Add consideration and instruction", cwd=tmp_path)

    run_prompt(cwd=tmp_path)
    out = capsys.readouterr().out
    types = [line.strip() for line in out.splitlines() if line.startswith("[")]
    assert types == ["[a_header]", "[b_consideration]", "[c_instruction]"]


def test_commit_rejects_partial_commit_with_new_types(tmp_path, monkeypatch) -> None:
    """Partial commit adding new types raises PartialCommitAddsNewTypeError."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_a_header.j2").write_text("Header")
    (tmp_path / "02_b_consideration.j2").write_text("Consideration")
    (tmp_path / "03_c_instruction.j2").write_text("Instruction")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit_paths(
        message="First",
        paths=[tmp_path / "01_a_header.j2", tmp_path / "02_b_consideration.j2"],
        cwd=tmp_path,
    )

    with pytest.raises(PartialCommitAddsNewTypeError) as exc_info:
        run_commit_paths(
            message="Add instruction",
            paths=[tmp_path / "03_c_instruction.j2"],
            cwd=tmp_path,
        )
    assert "instruction" in str(exc_info.value)


def test_commit_rejects_partial_commit_when_uncommitted_type_has_no_cwd_file(
    tmp_path, monkeypatch
) -> None:
    """Partial commit raises when an uncommitted type has no .j2 file in CWD."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_a_header.j2").write_text("Header")
    (tmp_path / "02_b_consideration.j2").write_text("Consideration")
    (tmp_path / "03_c_instruction.j2").write_text("Instruction")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit(message="All three", cwd=tmp_path)

    (tmp_path / "03_c_instruction.j2").unlink()
    with pytest.raises(PartialCommitMissingCwdFileError) as exc_info:
        run_commit_paths(
            message="Update consideration",
            paths=[tmp_path / "02_b_consideration.j2"],
            cwd=tmp_path,
        )
    assert "instruction" in str(exc_info.value)


def test_commit_allows_partial_update(tmp_path, monkeypatch, capsys) -> None:
    """Partial commit that only updates existing types preserves order."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_a_header.j2").write_text("Header")
    (tmp_path / "02_b_consideration.j2").write_text("Consideration v1")
    (tmp_path / "03_c_instruction.j2").write_text("Instruction")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit(message="All three", cwd=tmp_path)

    (tmp_path / "02_b_consideration.j2").write_text("Consideration v2")
    run_commit_paths(
        message="Update consideration",
        paths=[tmp_path / "02_b_consideration.j2"],
        cwd=tmp_path,
    )

    run_prompt(cwd=tmp_path)
    out = capsys.readouterr().out
    types = [line.strip() for line in out.splitlines() if line.startswith("[")]
    assert types == ["[a_header]", "[b_consideration]", "[c_instruction]"]


def test_commit_full_commit_drops_types_without_cwd_files(tmp_path, monkeypatch, capsys) -> None:
    """Full commit includes only types with files in CWD; types whose files were deleted are dropped."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_intro.j2").write_text("Intro")
    (tmp_path / "02_body.j2").write_text("Body")
    (tmp_path / "03_conclusion.j2").write_text("Conclusion")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit(message="All three", cwd=tmp_path)

    (tmp_path / "03_conclusion.j2").unlink()
    run_commit(message="Remove conclusion", cwd=tmp_path)

    run_prompt(cwd=tmp_path)
    out = capsys.readouterr().out
    types = [line.strip() for line in out.splitlines() if line.startswith("[")]
    assert types == ["[intro]", "[body]"]

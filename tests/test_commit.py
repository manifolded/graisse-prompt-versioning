"""Tests for commit type extraction and validation."""

import pytest

from gpv.commands.commit import (
    CwdFilenameValidationError,
    DuplicateTypeInCommitError,
    PartialCommitAddsNewTypeError,
    PartialCommitMissingCwdFileError,
    parse_filename,
    run_commit,
    run_commit_paths,
)
from gpv.commands.prompt import run_prompt
from gpv.config import get_db_path
from gpv.db import connect


def test_parse_filename() -> None:
    assert parse_filename("01_intro.j2") == ("01", "intro")
    assert parse_filename("01_intro_section.j2") == ("01", "intro_section")
    assert parse_filename("1_intro.j2") == ("1", "intro")
    assert parse_filename("001_body.j2") == ("001", "body")


def test_parse_filename_invalid() -> None:
    with pytest.raises(ValueError):
        parse_filename("intro.js")
    with pytest.raises(ValueError):
        parse_filename("a_intro")


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


def test_commit_rejects_inconsistent_prefix_format(tmp_path, monkeypatch) -> None:
    """Full commit with 1_intro.j2 and 02_body.j2 raises CwdFilenameValidationError."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "1_intro.j2").write_text("Intro")
    (tmp_path / "02_body.j2").write_text("Body")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    with pytest.raises(CwdFilenameValidationError) as exc_info:
        run_commit(message="Full commit", cwd=tmp_path)
    assert "inconsistent" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()


def test_commit_rejects_duplicate_prefixes(tmp_path, monkeypatch) -> None:
    """Full commit with 01_intro.j2 and 01_body.j2 raises CwdFilenameValidationError."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_intro.j2").write_text("Intro")
    (tmp_path / "01_body.j2").write_text("Body")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    with pytest.raises(CwdFilenameValidationError) as exc_info:
        run_commit(message="Test", cwd=tmp_path)
    assert "01" in str(exc_info.value) or "duplicate" in str(exc_info.value).lower()


def test_commit_rejects_non_consecutive_prefixes(tmp_path, monkeypatch) -> None:
    """Full commit with 01_intro.j2 and 03_instruction.j2 (missing 02) raises CwdFilenameValidationError."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_intro.j2").write_text("Intro")
    (tmp_path / "03_instruction.j2").write_text("Instruction")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    with pytest.raises(CwdFilenameValidationError) as exc_info:
        run_commit(message="Test", cwd=tmp_path)
    assert "consecutive" in str(exc_info.value).lower()


def test_commit_rejects_non_numeric_prefix(tmp_path, monkeypatch) -> None:
    """Full commit with a_intro.j2 raises CwdFilenameValidationError."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "a_intro.j2").write_text("Intro")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    with pytest.raises(CwdFilenameValidationError) as exc_info:
        run_commit(message="Test", cwd=tmp_path)
    assert "non-numeric" in str(exc_info.value).lower() or "a_intro" in str(exc_info.value)


def test_commit_allows_different_prefixes(tmp_path, monkeypatch, capsys) -> None:
    """01_intro.j2, 02_body.j2 — full commit succeeds."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_intro.j2").write_text("Intro")
    (tmp_path / "02_body.j2").write_text("Body")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit(message="Full commit", cwd=tmp_path)

    run_prompt(cwd=tmp_path)
    out = capsys.readouterr().out
    types = [line.strip() for line in out.splitlines() if line.startswith("[")]
    assert types == ["[intro]", "[body]"]


def test_commit_partial_rejects_duplicate_prefixes(tmp_path, monkeypatch) -> None:
    """Partial commit when CWD has duplicate prefix 01 raises CwdFilenameValidationError."""
    monkeypatch.chdir(tmp_path)
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "01_a.j2").write_text("A")
    (tmp_path / "02_b.j2").write_text("B")

    from gpv.commands import init

    init.run_init(cwd=tmp_path)

    run_commit_paths(
        message="First",
        paths=[tmp_path / "01_a.j2", tmp_path / "02_b.j2"],
        cwd=tmp_path,
    )

    (tmp_path / "01_c.j2").write_text("C")
    with pytest.raises(CwdFilenameValidationError) as exc_info:
        run_commit_paths(
            message="Update",
            paths=[tmp_path / "01_a.j2", tmp_path / "02_b.j2"],
            cwd=tmp_path,
        )
    assert "01" in str(exc_info.value) or "duplicate" in str(exc_info.value).lower()


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

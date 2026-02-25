"""Tests for commit type extraction and validation."""

import pytest

from gpv.commands.commit import (
    DuplicateTypeInCommitError,
    extract_type_from_filename,
    run_commit,
)
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

"""Integration test: uncommit restores database to state before last commit."""

from pathlib import Path

from gpv.commands import commit, init, uncommit
from gpv.config import get_db_path
from gpv.db import connect

from tests.test_utils import db_state


def test_uncommit_restores_database_state(tmp_path: Path) -> None:
    """Uncommit restores the database to its state before the last commit."""
    db_path = (tmp_path / "gpv.db").resolve()
    (tmp_path / ".gpv").write_text(str(db_path))
    (tmp_path / "a_intro.j2").write_text("Hello")
    (tmp_path / "b_body.j2").write_text("Body")

    init.run_init(cwd=tmp_path)
    commit.run_commit(message="First", paths=[tmp_path / "a_intro.j2"], cwd=tmp_path)

    conn = connect(get_db_path(tmp_path))
    try:
        state_after_first = db_state(conn)
    finally:
        conn.close()

    commit.run_commit(message="Second", paths=[tmp_path / "b_body.j2"], cwd=tmp_path)
    uncommit.run_uncommit(cwd=tmp_path, confirm=False)

    conn = connect(get_db_path(tmp_path))
    try:
        state_after_uncommit = db_state(conn)
    finally:
        conn.close()

    assert state_after_uncommit == state_after_first

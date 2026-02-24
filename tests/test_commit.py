"""Tests for commit type extraction."""

import pytest

from gpv.commands.commit import extract_type_from_filename


def test_extract_type() -> None:
    assert extract_type_from_filename("a_intro.j2") == "intro"
    assert extract_type_from_filename("a_intro_section.j2") == "intro_section"
    assert extract_type_from_filename("01_intro.j2") == "intro"
    assert extract_type_from_filename("01a_intro.j2") == "intro"


def test_extract_type_invalid() -> None:
    with pytest.raises(ValueError):
        extract_type_from_filename("intro.js")
        extract_type_from_filename("a_intro")

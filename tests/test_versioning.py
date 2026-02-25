"""Tests for versioning logic."""

import pytest

from gpv.versioning import branch_version, increment_version, is_branched, version_gt


def test_increment_first_of_type() -> None:
    assert increment_version(None) == "1"


def test_increment_simple() -> None:
    assert increment_version("4.23") == "4.24"
    assert increment_version("1") == "2"


def test_branch() -> None:
    assert branch_version("4.3") == "4.3.1"
    assert branch_version("1") == "1.1"


def test_is_branched() -> None:
    assert is_branched("4.3.1", "4.3") is True
    assert is_branched("4.4", "4.3") is False
    assert is_branched("4.3", "4.3") is False


def test_version_gt() -> None:
    assert version_gt("4.4", "4.3") is True
    assert version_gt("4.3.1", "4.3") is True
    assert version_gt("4.3", "4.3.1") is False
    assert version_gt("4.3", "4.3") is False
    assert version_gt("4.2", "4.1.1") is True

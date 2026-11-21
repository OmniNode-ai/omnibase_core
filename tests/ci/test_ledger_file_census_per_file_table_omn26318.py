# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The ledger file census ratchet carries a per-file table (OMN-26318).

``config/ledger_file_census_ratchet.yaml`` holds the shrink-only repository row
under ``ratchet`` and, beside it, the files that hold a ledger-file reader or
writer under ``files``, each with its line count. The table lets the census node
name the file that grew, not only the repository whose total rose. This module
pins the table's shape:

* a ``files.omnibase_core`` table exists, and every row is a non-empty repository
  relative path with a positive int line count;
* the table never holds more files than the repository row allows;
* the check refuses a ratchet file without the table, and one whose row is not a
  positive int (the failing controls).

At the merge base the ratchet file has no ``files`` table, so these tests fail
there and pass at the head.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
RATCHET_FILE = REPO_ROOT / "config" / "ledger_file_census_ratchet.yaml"
REPOSITORY = "omnibase_core"


def _check_per_file_table(ratchet: dict[str, Any]) -> None:
    """Assert the parsed ratchet file carries a well-formed per-file table.

    Takes the parsed ratchet file so a failing control can hand it a modified copy.
    """
    files = (ratchet.get("files") or {}).get(REPOSITORY)
    assert isinstance(files, dict) and files, (
        f"config/ledger_file_census_ratchet.yaml needs a non-empty files.{REPOSITORY} table"
    )
    for path, lines in files.items():
        assert isinstance(path, str) and path and not path.startswith("/"), (
            f"per-file row {path!r} must be a repository-relative path"
        )
        assert isinstance(lines, int) and not isinstance(lines, bool) and lines > 0, (
            f"per-file row {path!r} must be a positive int line count, got {lines!r}"
        )
    row = ratchet["ratchet"][REPOSITORY]
    assert len(files) <= row, (
        f"the per-file table lists {len(files)} files but the {REPOSITORY} row allows {row}"
    )


def _load() -> dict[str, Any]:
    loaded = yaml.safe_load(RATCHET_FILE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_the_ratchet_file_carries_a_per_file_table() -> None:
    _check_per_file_table(_load())


def test_the_per_file_table_covers_the_repository_row() -> None:
    ratchet = _load()
    files = ratchet["files"][REPOSITORY]
    assert len(files) == ratchet["ratchet"][REPOSITORY], (
        "the measured per-file table must list exactly as many files as the "
        "repository row counts"
    )


def test_a_ratchet_file_without_the_table_fails_the_check() -> None:
    """The failing control: the check must refuse a ratchet file with no table."""
    stripped = copy.deepcopy(_load())
    del stripped["files"]
    with pytest.raises(AssertionError, match="needs a non-empty"):
        _check_per_file_table(stripped)


def test_a_non_positive_per_file_row_fails_the_check() -> None:
    broken = copy.deepcopy(_load())
    first = next(iter(broken["files"][REPOSITORY]))
    broken["files"][REPOSITORY][first] = 0
    with pytest.raises(AssertionError, match="positive int"):
        _check_per_file_table(broken)

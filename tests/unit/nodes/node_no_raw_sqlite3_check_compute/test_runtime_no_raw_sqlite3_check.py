# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-raw-sqlite3-check CLI runtime (OMN-14659, OMN-13305 pattern).

Covers both invocation modes: pre-commit's explicit-filenames mode (I/O read
directly at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoRawSqlite3CheckCompute`` handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_raw_sqlite3_check_compute.runtime_no_raw_sqlite3_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_main_filenames_mode_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text("db = injected_adapter.connect()\n")

    exit_code = main([str(clean)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No raw sqlite3.connect() calls found outside adapter definitions" in out


def test_main_filenames_mode_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('import sqlite3\nconn = sqlite3.connect("db.sqlite")\n')

    exit_code = main([str(bad)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert (
        "FAIL: Found 1 raw sqlite3.connect() call(s) outside adapter definitions:"
        in out
    )
    assert "raw sqlite3.connect() call" in out


def test_main_filenames_mode_skips_non_python_and_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_python = tmp_path / "notes.md"
    not_python.write_text("sqlite3.connect() mentioned in prose\n")
    missing = tmp_path / "missing.py"

    exit_code = main([str(not_python), str(missing)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No raw sqlite3.connect() calls found outside adapter definitions" in out


def test_main_filenames_mode_adapter_suffix_excluded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    adapter = tmp_path / "session_adapter.py"
    adapter.write_text('import sqlite3\nconn = sqlite3.connect("db.sqlite")\n')

    exit_code = main([str(adapter)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No raw sqlite3.connect() calls found outside adapter definitions" in out


def test_main_full_tree_mode_walks_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text('import sqlite3\nconn = sqlite3.connect("db.sqlite")\n')
    (src / "clean.py").write_text("db = injected_adapter.connect()\n")

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert (
        "FAIL: Found 1 raw sqlite3.connect() call(s) outside adapter definitions:"
        in out
    )
    assert "bad.py" in out


def test_main_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    exit_code = main(["--root", str(empty_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No raw sqlite3.connect() calls found outside adapter definitions" in out


def test_main_syntax_error_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n    pass\n")

    exit_code = main([str(broken)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert (
        "FAIL: Found 1 raw sqlite3.connect() call(s) outside adapter definitions:"
        in out
    )

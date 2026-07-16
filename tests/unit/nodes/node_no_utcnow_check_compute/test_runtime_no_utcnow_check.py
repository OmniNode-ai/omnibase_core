# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-utcnow-check CLI runtime (OMN-14656, OMN-13305 pattern).

Covers both invocation modes: pre-commit's explicit-filenames mode (I/O read
directly at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoUtcnowCheckCompute`` handler, and exit codes/summary output are
asserted for both PASS and FAIL outcomes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_utcnow_check_compute.runtime_no_utcnow_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_main_filenames_mode_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text(
        "from datetime import datetime, timezone\nts = datetime.now(timezone.utc)\n"
    )

    exit_code = main([str(clean)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No datetime.utcnow() usage found" in out


def test_main_filenames_mode_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("import datetime\nts = datetime.utcnow()\n")

    exit_code = main([str(bad)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 finding(s)" in out
    assert "use of datetime.utcnow()" in out


def test_main_filenames_mode_skips_non_python_and_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_python = tmp_path / "notes.md"
    not_python.write_text("datetime.utcnow() mentioned in prose\n")
    missing = tmp_path / "missing.py"

    exit_code = main([str(not_python), str(missing)])

    assert exit_code == 0
    assert "OK: No datetime.utcnow() usage found" in capsys.readouterr().out


def test_main_filenames_mode_unreadable_python_exits_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreadable = tmp_path / "unreadable.py"
    unreadable.write_text("from datetime import datetime\n")
    original_read_text = Path.read_text

    def fake_read_text(
        self: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if self == unreadable:
            raise OSError("permission denied")
        return original_read_text(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    exit_code = main([str(unreadable)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ERROR: Failed to read 1 Python file(s)" in out
    assert "unreadable.py: read error: permission denied" in out


def test_main_full_tree_mode_walks_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text("import datetime\nts = datetime.utcnow()\n")
    (src / "clean.py").write_text("import time\nnow = time.time()\n")

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 finding(s)" in out
    assert "bad.py" in out


def test_main_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    exit_code = main(["--root", str(empty_root)])

    assert exit_code == 0
    assert "OK: No datetime.utcnow() usage found" in capsys.readouterr().out


def test_main_syntax_error_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n    pass\n")

    exit_code = main([str(broken)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ERROR: Found 1 finding(s)" in out

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-env-fallbacks-check CLI runtime (OMN-14659, OMN-13305 pattern).

Covers both invocation modes: pre-commit's explicit-filenames mode (I/O read
directly at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoEnvFallbacksCheckCompute`` handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_env_fallbacks_check_compute.runtime_no_env_fallbacks_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_main_filenames_mode_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text('host = os.environ["PG_HOST"]\n')

    exit_code = main([str(clean)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PASS: No localhost/hardcoded-endpoint fallbacks found." in out


def test_main_filenames_mode_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('host = os.environ.get("PG_HOST", "localhost")\n')

    exit_code = main([str(bad)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: 1 localhost/hardcoded-endpoint fallback(s) found:" in out
    assert "localhost" in out


def test_main_filenames_mode_scans_shell_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.sh"
    bad.write_text('HOST="${PG_HOST:-localhost}"\n')

    exit_code = main([str(bad)])

    assert exit_code == 1
    assert (
        "FAIL: 1 localhost/hardcoded-endpoint fallback(s) found:"
        in capsys.readouterr().out
    )


def test_main_filenames_mode_skips_non_scanned_and_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_scanned = tmp_path / "notes.md"
    not_scanned.write_text('host = os.environ.get("PG_HOST", "localhost")\n')
    missing = tmp_path / "missing.py"

    exit_code = main([str(not_scanned), str(missing)])

    assert exit_code == 0
    assert (
        "PASS: No localhost/hardcoded-endpoint fallbacks found."
        in capsys.readouterr().out
    )


def test_main_full_tree_mode_walks_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text('host = os.environ.get("PG_HOST", "localhost")\n')
    (src / "clean.py").write_text('host = os.environ["PG_HOST"]\n')

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: 1 localhost/hardcoded-endpoint fallback(s) found:" in out
    assert "bad.py" in out


def test_main_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    exit_code = main(["--root", str(empty_root)])

    assert exit_code == 0
    assert (
        "PASS: No localhost/hardcoded-endpoint fallbacks found."
        in capsys.readouterr().out
    )

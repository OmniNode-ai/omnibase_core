# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-hardcoded-ip-check CLI runtime (OMN-14659, OMN-13305 pattern).

Covers both invocation modes: pre-commit's explicit-filenames mode (I/O read
directly at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoHardcodedIpCheckCompute`` handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.runtime_no_hardcoded_ip_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_main_filenames_mode_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text('BROKER = os.environ["KAFKA_BOOTSTRAP_SERVERS"]\n')

    exit_code = main([str(clean)])

    assert exit_code == 0
    assert "OK: No hardcoded internal IPs found" in capsys.readouterr().out


def test_main_filenames_mode_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('BROKER = "192.168.86.201"\n')

    exit_code = main([str(bad)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ERROR: 1 hardcoded internal IP(s) found:" in out
    assert "192.168.86.201" in out


def test_main_filenames_mode_scans_yaml_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text('broker: "10.0.0.5"\n')

    exit_code = main([str(bad)])

    assert exit_code == 1
    assert "ERROR: 1 hardcoded internal IP(s) found:" in capsys.readouterr().out


def test_main_filenames_mode_skips_non_scanned_and_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_scanned = tmp_path / "notes.md"
    not_scanned.write_text("192.168.86.201 mentioned in prose\n")
    missing = tmp_path / "missing.py"

    exit_code = main([str(not_scanned), str(missing)])

    assert exit_code == 0
    assert "OK: No hardcoded internal IPs found" in capsys.readouterr().out


def test_main_full_tree_mode_walks_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text('BROKER = "192.168.86.201"\n')
    (src / "clean.py").write_text('public_dns = "8.8.8.8"\n')

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ERROR: 1 hardcoded internal IP(s) found:" in out
    assert "bad.py" in out


def test_main_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    exit_code = main(["--root", str(empty_root)])

    assert exit_code == 0
    assert "OK: No hardcoded internal IPs found" in capsys.readouterr().out

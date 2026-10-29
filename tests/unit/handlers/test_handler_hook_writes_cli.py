# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the check-hook-writes CLI (OMN-21498, plan task T2.6).

The CLI reads the overlay and the hook files, runs the pure handler and exits 0
on PASS and 1 on FAIL or ERROR. It never reports PASS for a scan that read no
hook, and it is run over this repository's own hook files as the positive
control: no hook of the repository rewrites a file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.handlers.handler_hook_writes_cli import DEFAULT_OVERLAY, main

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_WRITER = (
    "repos:\n  - repo: local\n    hooks:\n"
    "      - id: tidy\n        name: tidy\n        entry: ruff format\n"
    "        language: system\n"
)
_CHECKER = _WRITER.replace("ruff format", "ruff format --check").replace("tidy", "tidy")


def _repo(tmp_path: Path, config: str | None, overlay: bool = True) -> Path:
    if config is not None:
        (tmp_path / ".pre-commit-config.yaml").write_text(config, encoding="utf-8")
    if overlay:
        (tmp_path / DEFAULT_OVERLAY).write_text(
            (_ROOT / DEFAULT_OVERLAY).read_text(encoding="utf-8"), encoding="utf-8"
        )
    return tmp_path


def test_writer_hook_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, _WRITER)
    assert main(["--root", str(root)]) == 1
    assert "tidy" in capsys.readouterr().out


def test_check_only_hook_exits_zero_and_leaves_bytes(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CHECKER)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    assert main(["--root", str(root)]) == 0
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_missing_overlay_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, _CHECKER, overlay=False)
    assert main(["--root", str(root)]) == 1
    assert "overlay" in capsys.readouterr().out


def test_zero_hooks_scanned_is_an_error_not_a_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, "repos: []\n")
    assert main(["--root", str(root)]) == 1
    assert "zero hooks" in capsys.readouterr().out


def test_missing_hook_files_is_an_error(tmp_path: Path) -> None:
    assert main(["--root", str(_repo(tmp_path, None))]) == 1


def test_unparseable_config_exits_one(tmp_path: Path) -> None:
    assert main(["--root", str(_repo(tmp_path, "repos: [unclosed"))]) == 1


def test_report_json_is_written(tmp_path: Path) -> None:
    root = _repo(tmp_path, _WRITER)
    report = tmp_path / "out" / "report.json"
    assert main(["--root", str(root), "--report-json", str(report)]) == 1
    assert json.loads(report.read_text(encoding="utf-8"))["overall_status"] == "FAIL"


def test_this_repository_has_no_rewriting_hook(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Positive control: the repo's own hook files pass, and were read."""
    assert main(["--root", str(_ROOT)]) == 0
    assert "hooks scanned" in capsys.readouterr().out

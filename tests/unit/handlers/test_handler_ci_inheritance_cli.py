# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ci-inheritance handler CLI (OMN-17427)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.handlers.handler_ci_inheritance_cli import (
    main,
)

pytestmark = pytest.mark.unit

_OTHER = (
    "jobs:\n  a:\n"
    "    uses: OmniNode-ai/omniclaude/.github/workflows/x-reusable.yml@abc\n"
)
_CORE = (
    "jobs:\n  a:\n"
    "    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@abc\n"
)


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base"
    head = tmp_path / "head"
    base.mkdir()
    head.mkdir()
    return base, head


def test_main_fails_on_added_non_host_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CORE)
    (head / "ci.yml").write_text(_CORE)
    (head / "new.yaml").write_text(_OTHER)

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: 1 new reusable CI reference(s)" in out
    assert "OmniNode-ai/omniclaude/.github/workflows/x-reusable.yml" in out


def test_main_passes_with_existing_debt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_OTHER)
    (head / "ci.yml").write_text(_OTHER.replace("@abc", "@def"))

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: no new reusable CI reference" in out
    assert "1 existing reference(s)" in out


def test_main_errors_when_head_dir_is_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 1
    assert "ERROR" in capsys.readouterr().out


def test_main_errors_when_base_dir_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, head = _dirs(tmp_path)
    (head / "ci.yml").write_text(_CORE)

    exit_code = main(["--base-dir", str(tmp_path / "absent"), "--head-dir", str(head)])

    assert exit_code == 1
    assert "ERROR" in capsys.readouterr().out


_CI_LINT = (
    "on:\n  pull_request:\njobs:\n  lint:\n    runs-on: ubuntu-latest\n"
    "    steps:\n      - run: ruff check\n"
)
_NEW_JOB = "  typecheck:\n    runs-on: ubuntu-latest\n    steps:\n      - run: mypy\n"


def test_main_fails_on_added_repository_specific_job(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CI_LINT)
    (head / "ci.yml").write_text(_CI_LINT + _NEW_JOB)

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: 1 new repository-specific CI job(s)" in out
    assert "ci.yml:jobs.typecheck" in out


def test_main_passes_with_existing_repository_specific_jobs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CI_LINT)
    (head / "ci.yml").write_text(_CI_LINT.replace("ruff check", "ruff check --fix"))

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "1 existing repository-specific job(s)" in out


def test_main_repository_flag_judges_a_non_host_reusable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    reusable = _CI_LINT.replace("on:\n  pull_request:\n", "on:\n  workflow_call:\n")
    (head / "lint-reusable.yml").write_text(reusable)

    host_exit = main(["--base-dir", str(base), "--head-dir", str(head)])
    other_exit = main(
        [
            "--base-dir",
            str(base),
            "--head-dir",
            str(head),
            "--repository",
            "omnibase_spi",
        ]
    )

    assert host_exit == 0
    assert other_exit == 1
    assert "lint-reusable.yml:jobs.lint" in capsys.readouterr().out

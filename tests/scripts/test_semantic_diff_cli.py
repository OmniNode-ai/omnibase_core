# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for scripts/analysis/semantic_diff.py CLI (OMN-10375)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "analysis" / "semantic_diff.py"

# Ensure the worktree src takes precedence when running subprocess CLI calls.
# The editable .pth install may resolve to the canonical clone if it appears
# earlier on sys.path, which lacks not-yet-merged subpackages from stacked branches.
_WORKTREE_SRC = str(REPO_ROOT / "src")
_SUBPROCESS_ENV = {
    **os.environ,
    "PYTHONPATH": _WORKTREE_SRC + os.pathsep + os.environ.get("PYTHONPATH", ""),
}


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: PLW1510
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_SUBPROCESS_ENV,
    )


@pytest.mark.unit
def test_cli_exits_0_with_json_flag() -> None:
    """CLI exits 0 even when critical changes are detected (advisory mode)."""
    result = _run_cli("--base", "origin/main", "--head", "HEAD", "--json")
    assert result.returncode == 0, f"stderr: {result.stderr}"


@pytest.mark.unit
def test_cli_json_output_validates_against_model() -> None:
    """JSON output validates against ModelSemanticDiffReport via a subprocess round-trip."""
    # Validate via subprocess so the worktree src path takes precedence cleanly.
    # In-process import resolves to the editable-installed canonical clone which
    # lacks not-yet-merged subpackages from stacked branches.
    result = _run_cli("--base", "origin/main", "--head", "HEAD", "--json")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(result.stdout)
        tmp_path = f.name

    validate_script = (
        "import sys, json;"
        f"sys.path.insert(0, {_WORKTREE_SRC!r});"
        "from omnibase_core.models.analysis.model_semantic_diff_report import ModelSemanticDiffReport;"
        f"data = json.load(open({tmp_path!r}));"
        "r = ModelSemanticDiffReport.model_validate(data);"
        "assert isinstance(r.changes, tuple);"
        "assert isinstance(r.total_consumers_affected, int);"
        "print('ok')"
    )
    val_result = subprocess.run(  # noqa: PLW1510
        [sys.executable, "-c", validate_script],
        capture_output=True,
        text=True,
        env=_SUBPROCESS_ENV,
    )
    Path(tmp_path).unlink(missing_ok=True)
    assert val_result.returncode == 0, f"Validation failed: {val_result.stderr}"
    assert val_result.stdout.strip() == "ok"


@pytest.mark.unit
def test_cli_json_has_required_fields() -> None:
    """JSON output has changes list and total_consumers_affected."""
    result = _run_cli("--base", "origin/main", "--head", "HEAD", "--json")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert "changes" in payload
    assert "total_consumers_affected" in payload
    assert isinstance(payload["changes"], list)
    assert isinstance(payload["total_consumers_affected"], int)


@pytest.mark.unit
def test_cli_missing_required_args_exits_nonzero() -> None:
    """CLI exits non-zero when required --base / --head args are absent."""
    result = _run_cli("--json")
    assert result.returncode != 0


@pytest.mark.unit
def test_cli_unavailable_base_ref_emits_empty_advisory_report() -> None:
    """CLI stays advisory when a shallow checkout lacks the requested base ref."""
    result = _run_cli(
        "--base", "refs/heads/omn-missing-base", "--head", "HEAD", "--json"
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "base ref" in result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"changes": [], "total_consumers_affected": 0}


@pytest.mark.unit
def test_cli_json_change_fields() -> None:
    """Each change entry has the required fields."""
    result = _run_cli("--base", "origin/main", "--head", "HEAD", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    for change in payload["changes"]:
        assert "kind" in change
        assert "severity" in change
        assert "symbol_name" in change
        assert "file_path" in change
        assert "consumers_count" in change

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for scripts/validation/validate-check-names.py (OMN-11119).

Covers:
- _parse_workflow_file: job_uses populated for workflow_call jobs
- _validate_gates: WORKFLOW_CALL_COMPOSITE_NAME_MISMATCH for jobs with uses:
- _validate_gates: composite name passes when check_name has correct prefix
- Regression: non-workflow_call jobs still use CHECK_NAME_MISMATCH path
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validation" / "validate-check-names.py"


def _load_module():  # type: ignore[return]
    spec = importlib.util.spec_from_file_location("validate_check_names", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()
_parse_workflow_file = _mod._parse_workflow_file
_parse_required_checks = _mod._parse_required_checks
_validate_gates = _mod._validate_gates


def _write_workflow(tmp_path: Path, name: str, content: str) -> Path:
    wf = tmp_path / name
    wf.write_text(textwrap.dedent(content).lstrip())
    return wf


@pytest.mark.unit
def test_parse_workflow_file_detects_uses_reference(tmp_path: Path) -> None:
    """job_uses is populated for a job that calls a reusable workflow via uses:."""
    wf = _write_workflow(
        tmp_path,
        "call-reject-skip.yml",
        """
        name: Reject skip-gate bypass tokens
        on:
          pull_request:
        jobs:
          call-reject-skip-token:
            uses: OmniNode-ai/omniclaude/.github/workflows/reject-deploy-gate-skip.yml@main
            secrets: inherit
        """,
    )
    info = _parse_workflow_file(wf)
    assert "call-reject-skip-token" in info.job_keys
    assert info.job_uses.get("call-reject-skip-token") == (
        "OmniNode-ai/omniclaude/.github/workflows/reject-deploy-gate-skip.yml@main"
    )
    assert "call-reject-skip-token" not in info.job_names


@pytest.mark.unit
def test_parse_workflow_file_no_uses_for_regular_job(tmp_path: Path) -> None:
    """job_uses is empty for jobs that do not use workflow_call."""
    wf = _write_workflow(
        tmp_path,
        "ci.yml",
        """
        name: CI
        on:
          push:
        jobs:
          quality-gate:
            name: Quality Gate
            runs-on: ubuntu-latest
            steps:
              - run: echo ok
        """,
    )
    info = _parse_workflow_file(wf)
    assert "quality-gate" in info.job_keys
    assert info.job_names.get("quality-gate") == "Quality Gate"
    assert info.job_uses == {}


@pytest.mark.unit
def test_validate_gates_composite_name_correct(tmp_path: Path) -> None:
    """No violation when check_name starts with '<caller-job-key> /' for a workflow_call job."""
    wf = _write_workflow(
        tmp_path,
        "call-reject-skip.yml",
        """
        name: Reject skip-gate bypass tokens
        on:
          pull_request:
        jobs:
          call-reject-skip-token:
            uses: OmniNode-ai/omniclaude/.github/workflows/reject-deploy-gate-skip.yml@main
            secrets: inherit
        """,
    )
    gates = [
        {
            "check_name": "call-reject-skip-token / scan / reject-skip-gate-token",
            "workflow_file": "call-reject-skip.yml",
            "workflow_job_key": "call-reject-skip-token",
        }
    ]
    violations = _validate_gates(gates, tmp_path)
    assert violations == [], f"Unexpected violations: {violations}"


@pytest.mark.unit
def test_validate_gates_composite_name_missing_prefix(tmp_path: Path) -> None:
    """WORKFLOW_CALL_COMPOSITE_NAME_MISMATCH when check_name lacks '<caller-job-key> /' prefix."""
    wf = _write_workflow(
        tmp_path,
        "call-reject-skip.yml",
        """
        name: Reject skip-gate bypass tokens
        on:
          pull_request:
        jobs:
          call-reject-skip-token:
            uses: OmniNode-ai/omniclaude/.github/workflows/reject-deploy-gate-skip.yml@main
            secrets: inherit
        """,
    )
    gates = [
        {
            "check_name": "scan / reject-skip-gate-token",
            "workflow_file": "call-reject-skip.yml",
            "workflow_job_key": "call-reject-skip-token",
        }
    ]
    violations = _validate_gates(gates, tmp_path)
    assert len(violations) == 1
    assert violations[0].error_type == "WORKFLOW_CALL_COMPOSITE_NAME_MISMATCH"
    assert "call-reject-skip-token / " in violations[0].detail


@pytest.mark.unit
def test_validate_gates_regular_job_check_name_mismatch(tmp_path: Path) -> None:
    """CHECK_NAME_MISMATCH still fires for regular (non-workflow_call) jobs."""
    wf = _write_workflow(
        tmp_path,
        "ci.yml",
        """
        name: CI
        on:
          push:
        jobs:
          quality-gate:
            name: Quality Gate
            runs-on: ubuntu-latest
            steps:
              - run: echo ok
        """,
    )
    gates = [
        {
            "check_name": "wrong-name",
            "workflow_file": "ci.yml",
            "workflow_job_key": "quality-gate",
        }
    ]
    violations = _validate_gates(gates, tmp_path)
    assert len(violations) == 1
    assert violations[0].error_type == "CHECK_NAME_MISMATCH"


@pytest.mark.unit
def test_validate_gates_regular_job_check_name_correct(tmp_path: Path) -> None:
    """No violation when check_name matches display name for a regular job."""
    wf = _write_workflow(
        tmp_path,
        "ci.yml",
        """
        name: CI
        on:
          push:
        jobs:
          quality-gate:
            name: Quality Gate
            runs-on: ubuntu-latest
            steps:
              - run: echo ok
        """,
    )
    gates = [
        {
            "check_name": "Quality Gate",
            "workflow_file": "ci.yml",
            "workflow_job_key": "quality-gate",
        }
    ]
    violations = _validate_gates(gates, tmp_path)
    assert violations == [], f"Unexpected violations: {violations}"


@pytest.mark.unit
def test_validate_gates_workflow_call_any_callee_name_valid(tmp_path: Path) -> None:
    """Any check_name with the correct caller prefix is accepted (callee name is opaque)."""
    _write_workflow(
        tmp_path,
        "call-some-reusable.yml",
        """
        name: Call reusable
        on:
          pull_request:
        jobs:
          call-some-job:
            uses: org/repo/.github/workflows/reusable.yml@main
        """,
    )
    for callee_suffix in [
        "some-check",
        "scan / nested-check",
        "a / b / c",
    ]:
        gates = [
            {
                "check_name": f"call-some-job / {callee_suffix}",
                "workflow_file": "call-some-reusable.yml",
                "workflow_job_key": "call-some-job",
            }
        ]
        violations = _validate_gates(gates, tmp_path)
        assert violations == [], (
            f"Unexpected violations for '{callee_suffix}': {violations}"
        )

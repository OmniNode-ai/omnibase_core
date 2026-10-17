# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427: CodeRabbit is retired, so its review-thread gate is gone.

``cr-thread-gate.yml`` had been a no-op since CodeRabbit was retired; the
``gate`` caller job in ci.yml only kept the ``gate / CodeRabbit Thread Check``
context reporting. Live branch protection on ``dev`` does not list that context,
so removing the job cannot wedge a merge. Nothing may produce, require, anchor
or pin the context any more.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.ci.ci_summary_gate import GATE_JOBS, STRICT_SUCCESS_JOBS

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
REQUIRED_CHECKS = REPO_ROOT / ".github" / "required-checks.yaml"
RETIRED_CONTEXT = "gate / CodeRabbit Thread Check"


def test_cr_thread_gate_workflows_are_gone() -> None:
    assert not (WORKFLOWS_DIR / "cr-thread-gate.yml").exists()
    assert not (WORKFLOWS_DIR / "cr-thread-gate-caller.yml").exists()


def test_ci_yml_has_no_cr_thread_gate_caller() -> None:
    jobs = yaml.safe_load((WORKFLOWS_DIR / "ci.yml").read_text(encoding="utf-8"))[
        "jobs"
    ]
    assert "gate" not in jobs
    callers = [
        name
        for name, job in jobs.items()
        if "cr-thread-gate" in str(job.get("uses", ""))
    ]
    assert not callers
    for name, job in jobs.items():
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        assert "gate" not in needs, f"{name} still needs the retired gate job"


def test_required_checks_manifest_only_records_the_context_as_retired() -> None:
    # The required-context producer check (OMN-19037) refuses a dropped row, so
    # the manifest keeps one RETIRED row and nothing may require the context.
    manifest = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    rows = [g for g in manifest["gates"] if g["name"] == RETIRED_CONTEXT]
    assert [r["mode"] for r in rows] == ["RETIRED"]


def test_ci_summary_does_not_anchor_the_retired_context() -> None:
    assert RETIRED_CONTEXT not in GATE_JOBS
    assert RETIRED_CONTEXT not in STRICT_SUCCESS_JOBS

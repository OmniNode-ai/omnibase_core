# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: S6 part 2 retires core's OCC callers, mirroring omnibase_infra#4792."""

from pathlib import Path

import pytest
import yaml

from scripts.ci.ci_summary_gate import (
    EXTERNAL_CONTEXTS_BY_EVENT,
    GATE_JOBS,
    STRICT_SUCCESS_JOBS,
    external_contexts_for_event,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github/workflows"


def _workflows() -> dict[str, dict]:
    return {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(WORKFLOWS_DIR.glob("*.yml"))
    }


def test_no_occ_callers_in_workflow_uses() -> None:
    for filename, workflow in _workflows().items():
        if filename in {"occ-preflight.yml", "receipt-gate.yml"}:
            continue
        for job_id, job in workflow.get("jobs", {}).items():
            uses = job.get("uses", "")
            assert uses not in {
                "./.github/workflows/occ-preflight.yml",
                "./.github/workflows/receipt-gate.yml",
            }, (filename, job_id, uses)
            assert "omnibase_core/.github/workflows/occ-preflight.yml" not in uses
            assert not (
                "omniclaude/" in uses
                and any(
                    name in uses
                    for name in (
                        "call-occ-autobind-reusable.yml",
                        "call-occ-companion-effect-reusable.yml",
                    )
                )
            ), (filename, job_id, uses)


def test_no_occ_callers_in_job_dependencies() -> None:
    for filename, workflow in _workflows().items():
        for job_id, job in workflow.get("jobs", {}).items():
            needs = job.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            assert "occ-preflight" not in needs, (filename, job_id)
            assert "needs.occ-preflight" not in str(job.get("if", "")), (
                filename,
                job_id,
            )


def test_no_occ_callers_files_remain() -> None:
    for filename in (
        "call-occ-autobind.yml",
        "occ-companion-merge-heal.yml",
        "call-receipt-gate.yml",
    ):
        assert not (WORKFLOWS_DIR / filename).exists(), filename


def test_no_occ_callers_jobs_remain_in_ci() -> None:
    jobs = _workflows()["ci.yml"]["jobs"]
    assert (
        not {"occ-companion-effect", "occ-companion-merged", "contract-compliance"}
        & jobs.keys()
    )


def test_no_occ_callers_contexts_in_ci_summary() -> None:
    contexts = [*GATE_JOBS, *STRICT_SUCCESS_JOBS]
    for event_contexts in EXTERNAL_CONTEXTS_BY_EVENT.values():
        contexts.extend(event_contexts)
    for name in contexts:
        assert not any(
            token in name for token in ("OCC", "occ-", "Contract Compliance Check")
        ), name
    assert "repo-evidence / dod-verify" in external_contexts_for_event("pull_request")


def test_no_occ_callers_required_contexts() -> None:
    manifest = yaml.safe_load(
        (REPO_ROOT / ".github/required-checks.yaml").read_text(encoding="utf-8")
    )
    for row in manifest["gates"]:
        if row["mode"] == "REQUIRED":
            assert "occ-preflight" not in row["name"]
            assert row["name"] != "verify / verify"
            assert not row["name"].startswith("occ-companion-effect / ")


def test_no_occ_callers_comparison_in_repo_evidence() -> None:
    job = _workflows()["call-repo-evidence-gate.yml"]["jobs"]["repo-evidence"]
    assert job["with"]["compare-with-occ"] == "false"

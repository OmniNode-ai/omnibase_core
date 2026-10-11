# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074 - omnibase_core S6 part 1 of the OCC retirement.

Two changes, mirroring omnimarket#3398 and omnibase_infra#4775:

1. The skip-token scan no longer carries a change-control preflight.
   omniclaude#2540 (squash ``4358450cc`` on omniclaude ``dev``) removed the
   nested ``occ-preflight`` job from ``reject-deploy-gate-skip.yml``. This
   repository adopts it by its own pin bump, and the required-checks manifest
   and the CI Summary audit stop naming the nested context
   (``call-reject-skip-token / occ-preflight / eligibility``), because nothing
   produces it any more. The standalone ``occ-preflight / eligibility`` context
   stays declared until S6 part 2 deletes the OCC callers.

2. CI Summary expects ``repo-evidence / dod-verify`` on every ``pull_request``
   run (L4 ``EXPECTED_EXTERNAL_CONTEXTS``), so an absent repo-owned evidence
   verdict fails CI Summary as a red one does. The producer is
   ``call-repo-evidence-gate.yml`` on ``pull_request_target``: GitHub reads the
   base-branch definition and reports the verdict on the pull request head.

The nested context is still required by ``dev`` branch protection, so this
change lands in the cut-over window together with that protection change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from scripts.ci.ci_summary_gate import (
    EXPECTED_EXTERNAL_CONTEXTS,
    evaluate_external,
    external_contexts_for_event,
)
from tests.unit.scripts.ci.test_ci_summary_gate import DIRECT_REQUIRED_JOB_CONTEXTS

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CALLER = WORKFLOWS_DIR / "call-reject-skip.yml"
EVIDENCE_CALLER = WORKFLOWS_DIR / "call-repo-evidence-gate.yml"
REQUIRED_CHECKS = REPO_ROOT / ".github" / "required-checks.yaml"
REUSABLE = "OmniNode-ai/omniclaude/.github/workflows/reject-deploy-gate-skip.yml"
# The squash commit of omniclaude#2540 on omniclaude dev, by its abbreviated
# sha; the pin itself must be the full 40-character sha.
PREFLIGHT_FREE_SHA_PREFIX = "4358450cc"
NESTED_PREFLIGHT = "call-reject-skip-token / occ-preflight / eligibility"
SCAN = "call-reject-skip-token / scan / reject-skip-gate-token"
STANDALONE_PREFLIGHT = "occ-preflight / eligibility"
REPO_EVIDENCE = "repo-evidence / dod-verify"


def _caller_refs() -> list[str]:
    pattern = re.compile(rf"^\s*uses:\s*{re.escape(REUSABLE)}@(?P<ref>[^\s\"'#]+)")
    return [
        match["ref"]
        for line in CALLER.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
        for match in pattern.finditer(line)
    ]


def _check_run(name: str, conclusion: str | None, *, event: str) -> dict[str, object]:
    return {
        "id": 1,
        "name": name,
        "status": "completed" if conclusion else "in_progress",
        "conclusion": conclusion,
        "started_at": "2026-10-10T08:00:00Z",
        "completed_at": "2026-10-10T08:20:00Z" if conclusion else None,
        "event": event,
    }


def test_caller_pins_the_reusable_without_the_change_control_preflight() -> None:
    refs = _caller_refs()
    assert len(refs) == 1, refs
    assert re.fullmatch(r"[0-9a-f]{40}", refs[0]), refs
    assert refs[0].startswith(PREFLIGHT_FREE_SHA_PREFIX), refs


def test_required_checks_manifest_retires_the_nested_preflight_row() -> None:
    manifest = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    modes = {
        row["name"]: row["mode"] for row in manifest["gates"] if isinstance(row, dict)
    }
    # A dropped REQUIRED row needs a RETIRED row citing the ticket (OMN-19037).
    assert modes[NESTED_PREFLIGHT] == "RETIRED"
    nested = next(row for row in manifest["gates"] if row["name"] == NESTED_PREFLIGHT)
    assert "OMN-20074" in nested["rationale"]
    assert modes[SCAN] == "REQUIRED"
    assert modes[STANDALONE_PREFLIGHT] == "REQUIRED"


def test_ci_summary_audit_no_longer_maps_the_caller_to_the_nested_preflight() -> None:
    assert DIRECT_REQUIRED_JOB_CONTEXTS[
        ("call-reject-skip.yml", "call-reject-skip-token")
    ] == (SCAN,)


def test_ci_summary_expects_repo_evidence_on_pull_request_runs_only() -> None:
    assert REPO_EVIDENCE in EXPECTED_EXTERNAL_CONTEXTS
    assert REPO_EVIDENCE in external_contexts_for_event("pull_request")
    for event_name in ("push", "merge_group", "workflow_dispatch", "schedule"):
        assert REPO_EVIDENCE not in external_contexts_for_event(event_name)


def test_absent_repo_evidence_verdict_holds_ci_summary() -> None:
    others = [
        _check_run(name, "success", event="pull_request")
        for name in EXPECTED_EXTERNAL_CONTEXTS
        if name != REPO_EVIDENCE
    ]
    failures, missing = evaluate_external(others)
    assert failures == []
    assert missing == [REPO_EVIDENCE]


def test_red_repo_evidence_verdict_fails_ci_summary() -> None:
    rows = [
        _check_run(name, "success", event="pull_request")
        for name in EXPECTED_EXTERNAL_CONTEXTS
        if name != REPO_EVIDENCE
    ]
    rows.append(_check_run(REPO_EVIDENCE, "failure", event="pull_request_target"))
    failures, missing = evaluate_external(rows)
    assert failures == [REPO_EVIDENCE]
    assert missing == []


def test_green_base_branch_trigger_row_satisfies_ci_summary() -> None:
    rows = [
        _check_run(name, "success", event="pull_request")
        for name in EXPECTED_EXTERNAL_CONTEXTS
        if name != REPO_EVIDENCE
    ]
    rows.append(_check_run(REPO_EVIDENCE, "success", event="pull_request_target"))
    assert evaluate_external(rows) == ([], [])


def test_evidence_caller_keeps_comparing_with_occ_until_part_2() -> None:
    # S5 is still counting on omnibase_core: part 1 must not stop the
    # difference step. Part 2, which deletes the OCC callers, sets it "false".
    job = yaml.safe_load(EVIDENCE_CALLER.read_text(encoding="utf-8"))["jobs"][
        "repo-evidence"
    ]
    assert job["with"]["compare-with-occ"] == "true"
    triggers = yaml.safe_load(EVIDENCE_CALLER.read_text(encoding="utf-8"))[True]
    assert set(triggers) == {"pull_request_target"}

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the count-locked pull_request-workflow ratchet (C7 / OMN-14907).

The live-airtight test proves the ratchet holds on the real repo. The frozen
``EXPECTED_BUDGET`` constant is the second half of the count lock — mirroring
OMN-14430's ``test_decorative_debt_is_the_reported_count`` — so the budget cannot
drift without a deliberate two-file edit. The planted-failure tests prove every
gap class the ratchet exists to catch is actually reachable (a ratchet you did
not watch reject something is decorative).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.validation.model_workflow_ratchet_gap import (
    WORKFLOW_RATCHET_GAP_CODES,
)
from omnibase_core.validation.validator_pull_request_workflow_ratchet import (
    live_pull_request_workflows,
    triggers_on_pull_request,
    verify_pull_request_workflow_ratchet,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = (
    REPO_ROOT / "architecture-handshakes" / "pull-request-workflow-budget.yaml"
)

# The count lock, frozen a SECOND time (the registry YAML holds the first copy).
# To move it you must edit BOTH this constant AND the registry `budget` — a
# deliberate, reviewed act. It is intended to move DOWN only (retiring a workflow
# lowers it; C2/C3/C4 drain toward a smaller number).
EXPECTED_BUDGET = 49


def _write_registry(path: Path, **overrides: object) -> None:
    doc: dict[str, object] = {
        "schema_version": 1,
        "budget": 0,
        "allowlisted_workflows": [],
        "waivers": [],
    }
    doc.update(overrides)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _write_pr_workflow(wf_dir: Path, name: str) -> None:
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / name).write_text(
        yaml.safe_dump(
            {
                "name": name,
                "on": {"pull_request": {}},
                "jobs": {"validate": {"name": "validate"}},
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Live airtight + frozen count lock
# ---------------------------------------------------------------------------
def test_live_ratchet_holds() -> None:
    """The real repo passes the ratchet: every live PR-triggered workflow is
    enumerated, no entry is stale, and the budget matches the allowlist."""
    gaps = verify_pull_request_workflow_ratchet(
        repo_root=REPO_ROOT, registry_path=REGISTRY_PATH
    )
    assert not gaps, "pull_request-workflow ratchet gaps:\n" + "\n".join(
        g.format() for g in gaps
    )


def test_budget_is_the_frozen_count() -> None:
    """Second half of the count lock. A change to the number of allowed
    PR-triggered workflows must edit BOTH the registry `budget` and this
    constant — no silent drift up (new decorative workflow) or down (a workflow
    quietly dropped without lowering the ratchet)."""
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert registry["budget"] == EXPECTED_BUDGET
    assert len(registry["allowlisted_workflows"]) == EXPECTED_BUDGET


def test_registry_has_no_duplicate_allowlist_entries() -> None:
    """A duplicate line would let len(allowlist) match budget while under-covering
    the live set — reject it."""
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    allowlist = registry["allowlisted_workflows"]
    assert len(allowlist) == len(set(allowlist)), "duplicate allowlist entries"


# ---------------------------------------------------------------------------
# THE PROOF — planted seeded failures (one per gap class)
# ---------------------------------------------------------------------------
def test_planted_unregistered_workflow_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: a new pull_request-triggered workflow that is not
    enumerated anywhere must be flagged UNREGISTERED. This is the C7 §3 proof."""
    wf_dir = tmp_path / ".github" / "workflows"
    _write_pr_workflow(wf_dir, "seeded-unregistered.yml")
    registry = tmp_path / "budget.yaml"
    _write_registry(registry, budget=0, allowlisted_workflows=[])

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry
    )
    offenders = {(g.workflow_file, g.code) for g in gaps}
    assert ("seeded-unregistered.yml", "UNREGISTERED") in offenders


def test_planted_budget_growth_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: registering a net-new workflow (allowlist grows past
    budget) must fail BUDGET_MISMATCH — the count lock. Even though the file IS
    enumerated, the budget did not move, so it cannot silently grow."""
    wf_dir = tmp_path / ".github" / "workflows"
    _write_pr_workflow(wf_dir, "existing.yml")
    _write_pr_workflow(wf_dir, "net-new.yml")
    registry = tmp_path / "budget.yaml"
    # budget stays 1 while the author tried to register a second file.
    _write_registry(
        registry, budget=1, allowlisted_workflows=["existing.yml", "net-new.yml"]
    )

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry
    )
    codes = {g.code for g in gaps}
    assert "BUDGET_MISMATCH" in codes


def test_planted_stale_entry_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: an allowlist entry with no matching live file (a workflow
    retired without lowering the ratchet) must be flagged STALE."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    registry = tmp_path / "budget.yaml"
    _write_registry(registry, budget=1, allowlisted_workflows=["long-gone.yml"])

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry
    )
    offenders = {(g.workflow_file, g.code) for g in gaps}
    assert ("long-gone.yml", "STALE") in offenders


def test_planted_not_pr_triggered_entry_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: an allowlisted file that no longer triggers on
    pull_request (e.g. moved to workflow_dispatch-only) must be flagged
    NOT_PR_TRIGGERED — remove it and lower the budget."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "dispatch-only.yml").write_text(
        yaml.safe_dump(
            {
                "name": "dispatch-only",
                "on": {"workflow_dispatch": {}},
                "jobs": {"validate": {"name": "validate"}},
            }
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "budget.yaml"
    _write_registry(registry, budget=1, allowlisted_workflows=["dispatch-only.yml"])

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry
    )
    offenders = {(g.workflow_file, g.code) for g in gaps}
    assert ("dispatch-only.yml", "NOT_PR_TRIGGERED") in offenders


def test_planted_expired_waiver_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: a waiver past its expires date must fail WAIVER_EXPIRED so
    an exception cannot become permanent."""
    wf_dir = tmp_path / ".github" / "workflows"
    _write_pr_workflow(wf_dir, "waived.yml")
    registry = tmp_path / "budget.yaml"
    _write_registry(
        registry,
        budget=0,
        allowlisted_workflows=[],
        waivers=[
            {
                "workflow_file": "waived.yml",
                "ticket": "OMN-0000",
                "expires": "2026-07-20",
                "justification": "test",
                "retires": "nothing",
            }
        ],
    )

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry, today=date(2026, 7, 21)
    )
    offenders = {(g.workflow_file, g.code) for g in gaps}
    assert ("waived.yml", "WAIVER_EXPIRED") in offenders


def test_planted_incomplete_waiver_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: a waiver missing a required field must fail
    WAIVER_INCOMPLETE — a bare filename cannot buy an exemption."""
    wf_dir = tmp_path / ".github" / "workflows"
    _write_pr_workflow(wf_dir, "waived.yml")
    registry = tmp_path / "budget.yaml"
    _write_registry(
        registry,
        budget=0,
        allowlisted_workflows=[],
        waivers=[{"workflow_file": "waived.yml"}],
    )

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry, today=date(2026, 7, 21)
    )
    offenders = {(g.workflow_file, g.code) for g in gaps}
    assert ("waived.yml", "WAIVER_INCOMPLETE") in offenders


def test_valid_waiver_passes(tmp_path: Path) -> None:
    """A complete, unexpired waiver exempts a file from the budget WITHOUT
    counting toward it — so an intentional, tracked exception is honored."""
    wf_dir = tmp_path / ".github" / "workflows"
    _write_pr_workflow(wf_dir, "existing.yml")
    _write_pr_workflow(wf_dir, "waived.yml")
    registry = tmp_path / "budget.yaml"
    _write_registry(
        registry,
        budget=1,
        allowlisted_workflows=["existing.yml"],
        waivers=[
            {
                "workflow_file": "waived.yml",
                "ticket": "OMN-1234",
                "expires": "2026-12-31",
                "justification": "legitimate tracked exception",
                "retires": "some manual step",
            }
        ],
    )

    gaps = verify_pull_request_workflow_ratchet(
        repo_root=tmp_path, registry_path=registry, today=date(2026, 7, 21)
    )
    assert not gaps, "\n".join(g.format() for g in gaps)


# ---------------------------------------------------------------------------
# Malformed-registry + helper unit coverage
# ---------------------------------------------------------------------------
def test_malformed_budget_raises_value_error(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    registry = tmp_path / "budget.yaml"
    registry.write_text(
        yaml.safe_dump({"budget": "not-an-int", "allowlisted_workflows": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="budget"):
        verify_pull_request_workflow_ratchet(repo_root=tmp_path, registry_path=registry)


def test_bool_budget_rejected(tmp_path: Path) -> None:
    """YAML `true`/`false` are ints in Python — a bool budget must still be
    rejected, not silently treated as 0/1."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    registry = tmp_path / "budget.yaml"
    registry.write_text(
        yaml.safe_dump({"budget": True, "allowlisted_workflows": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="budget"):
        verify_pull_request_workflow_ratchet(repo_root=tmp_path, registry_path=registry)


def test_triggers_on_pull_request_forms() -> None:
    assert triggers_on_pull_request({"on": {"pull_request": {}}})
    assert triggers_on_pull_request({"on": ["pull_request", "push"]})
    assert triggers_on_pull_request({"on": "pull_request"})
    assert triggers_on_pull_request({"on": {"pull_request_target": {}}})
    # PyYAML parses bare `on:` as boolean-True key.
    assert triggers_on_pull_request({True: {"pull_request": {}}})
    assert not triggers_on_pull_request({"on": {"workflow_dispatch": {}}})
    assert not triggers_on_pull_request({"on": {"pull_request_review": {}}})


def test_gap_codes_are_closed_set() -> None:
    """Every code the model advertises is one the ratchet actually emits — no
    dead codes, and the planted tests above cover the reachable ones."""
    assert {
        "UNREGISTERED",
        "STALE",
        "NOT_PR_TRIGGERED",
        "BUDGET_MISMATCH",
        "WAIVER_EXPIRED",
        "WAIVER_INCOMPLETE",
    } == WORKFLOW_RATCHET_GAP_CODES


def test_live_pull_request_workflows_matches_registry() -> None:
    """Sanity: the helper's live enumeration equals the registry allowlist on the
    real repo (no waivers at baseline)."""
    live = set(live_pull_request_workflows(REPO_ROOT / ".github" / "workflows"))
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert live == set(registry["allowlisted_workflows"])

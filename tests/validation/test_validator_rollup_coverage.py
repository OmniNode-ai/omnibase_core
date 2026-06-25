# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Meta-check tests for Model-B rollup coverage (OMN-13574, epic OMN-13573).

Operator-locked decision: keep ONE required aggregate rollup context per repo,
but prove it is AIRTIGHT — the rollup job's transitive ``needs`` graph reaches a
real, non-failure-swallowing job for every opted-in spec-required validator.

These tests are the deterministic meta-check that a validator cannot be silently
dropped from the required rollup: removing a covering job from the rollup's
``needs``, deleting the job, or adding ``continue-on-error: true`` to it all turn
a test red. The first test also doubles as the planted-failure proof at the
rollup-needs-logic level (OMN-13574 step 5) — no live CI run needed to prove the
mechanism, though one is captured separately in the PR.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validation.validator_rollup_coverage import RollupCoverageVerifier

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = REPO_ROOT / "architecture-handshakes" / "validator-requirements.yaml"
PILOT_REPO = "omnibase_core"


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    with SPEC_PATH.open() as fh:
        return yaml.safe_load(fh)


def test_pilot_repo_is_opted_in(spec: dict[str, Any]) -> None:
    verifier = RollupCoverageVerifier(spec)
    assert verifier.is_opted_in(PILOT_REPO), (
        "omnibase_core must be listed under model_b_rollup_enforcement.repos"
    )


def test_live_ci_rollup_is_airtight() -> None:
    """The committed ci.yml must cover every opted-in spec-required validator."""
    verifier = RollupCoverageVerifier.from_spec_path(SPEC_PATH)
    gaps = verifier.verify_repo(repo_name=PILOT_REPO, repo_root=REPO_ROOT)
    assert not gaps, "rollup-coverage gaps in live ci.yml:\n" + "\n".join(
        f"  {g.validator} — {g.detail}" for g in gaps
    )


def test_non_opted_repo_returns_empty(spec: dict[str, Any]) -> None:
    """Repos not in the opt-in block are skipped (pilot scope; OMN-13576)."""
    verifier = RollupCoverageVerifier(spec)
    assert not verifier.is_opted_in("omnibase_spi")
    assert verifier.verify_repo(repo_name="omnibase_spi", repo_root=REPO_ROOT) == []


def _ci_workflow_dict() -> dict[str, Any]:
    with (REPO_ROOT / ".github" / "workflows" / "ci.yml").open() as fh:
        return yaml.safe_load(fh)


def _spec_with_inline_workflow(
    spec: dict[str, Any], workflow: dict[str, Any], tmp_path: Path
) -> tuple[RollupCoverageVerifier, Path]:
    """Build a verifier + a repo_root whose ci.yml is the mutated ``workflow``."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "ci.yml").write_text(yaml.safe_dump(workflow), encoding="utf-8")
    return RollupCoverageVerifier(spec), tmp_path


def test_planted_dropped_need_is_detected(spec: dict[str, Any], tmp_path: Path) -> None:
    """PLANTED FAILURE (step 5): drop a covering job from quality-gate.needs and
    confirm the verifier reports a coverage gap for that validator. This proves a
    validator silently dropped from the required rollup makes the gate red."""
    workflow = _ci_workflow_dict()
    needs = workflow["jobs"]["quality-gate"]["needs"]
    assert "aislop-patterns" in needs
    workflow["jobs"]["quality-gate"]["needs"] = [
        n for n in needs if n != "aislop-patterns"
    ]
    verifier, repo_root = _spec_with_inline_workflow(spec, workflow, tmp_path)
    gaps = verifier.verify_repo(repo_name=PILOT_REPO, repo_root=repo_root)
    offenders = {g.validator for g in gaps}
    assert "aislop-patterns" in offenders, (
        f"dropping aislop-patterns from the rollup needs must be detected; "
        f"gaps={offenders}"
    )


def test_planted_continue_on_error_is_detected(
    spec: dict[str, Any], tmp_path: Path
) -> None:
    """PLANTED FAILURE: marking a covering job continue-on-error: true swallows
    its failure before it reaches the rollup. The verifier must flag it."""
    workflow = _ci_workflow_dict()
    workflow["jobs"]["pydantic-patterns"]["continue-on-error"] = True
    verifier, repo_root = _spec_with_inline_workflow(spec, workflow, tmp_path)
    gaps = verifier.verify_repo(repo_name=PILOT_REPO, repo_root=repo_root)
    offenders = {g.validator for g in gaps}
    assert "pydantic-patterns" in offenders, (
        f"continue-on-error on a covering job must be detected; gaps={offenders}"
    )


def test_planted_deleted_job_is_detected(spec: dict[str, Any], tmp_path: Path) -> None:
    """Deleting the covering job entirely is a coverage gap."""
    workflow = _ci_workflow_dict()
    del workflow["jobs"]["naming-conventions"]
    # Remove the dangling need so the YAML stays internally consistent.
    workflow["jobs"]["quality-gate"]["needs"] = [
        n
        for n in workflow["jobs"]["quality-gate"]["needs"]
        if n != "naming-conventions"
    ]
    verifier, repo_root = _spec_with_inline_workflow(spec, workflow, tmp_path)
    gaps = verifier.verify_repo(repo_name=PILOT_REPO, repo_root=repo_root)
    offenders = {g.validator for g in gaps}
    assert "naming-conventions" in offenders


def test_wrong_rollup_context_name_is_detected(
    spec: dict[str, Any], tmp_path: Path
) -> None:
    """If the rollup job's name drifts from the required branch-protection
    context, the verifier flags the rollup itself."""
    mutated = copy.deepcopy(spec)
    mutated["model_b_rollup_enforcement"]["repos"][PILOT_REPO][
        "required_rollup_context"
    ] = "Not The Real Context"
    verifier = RollupCoverageVerifier(mutated)
    gaps = verifier.verify_repo(repo_name=PILOT_REPO, repo_root=REPO_ROOT)
    assert any(g.validator == "<rollup>" for g in gaps)


def test_meta_needs_superset_of_spec_required_validators(
    spec: dict[str, Any],
) -> None:
    """Meta-invariant: every validator declared in the Model-B validator_jobs map
    for the pilot is a real spec validator with ci_workflow: required that applies
    to the pilot repo. Guards against the map drifting away from the spec."""
    cfg = spec["model_b_rollup_enforcement"]["repos"][PILOT_REPO]
    required_validators = spec["required_validators"]
    for validator in cfg["validator_jobs"]:
        assert validator in required_validators, (
            f"validator_jobs references unknown validator {validator!r}"
        )
        entry = required_validators[validator]
        assert entry["ci_workflow"] == "required", (
            f"{validator!r} is mapped for rollup coverage but is not "
            f"ci_workflow: required in the spec"
        )
        applies = entry["applies_to_repos"]
        assert applies == "all" or PILOT_REPO in applies, (
            f"{validator!r} is mapped for rollup coverage but does not apply to "
            f"{PILOT_REPO}"
        )


def test_meta_full_equality_no_silent_escape(spec: dict[str, Any]) -> None:
    """STRONG meta-invariant (CodeRabbit #3): the set of ci_workflow:required
    validators that apply to the pilot must equal validator_jobs plus
    grandfathered_validators — exactly. A NEW required validator that starts
    applying to omnibase_core cannot silently escape Model B: it must be covered
    (validator_jobs) or explicitly deferred (grandfathered_validators). This is
    the reverse direction the forward-only check above could not catch."""
    verifier = RollupCoverageVerifier(spec)
    applicable = verifier.applicable_required_validators(PILOT_REPO)
    cfg = spec["model_b_rollup_enforcement"]["repos"][PILOT_REPO]
    mapped = set(cfg["validator_jobs"])
    grandfathered = set(cfg.get("grandfathered_validators", []))
    assert mapped.isdisjoint(grandfathered), (
        f"a validator is both mapped and grandfathered: {mapped & grandfathered}"
    )
    union = mapped | grandfathered
    escaped = applicable - union
    assert not escaped, (
        f"ci_workflow:required validators applying to {PILOT_REPO} that escape "
        f"Model B (neither covered nor grandfathered): {sorted(escaped)} — add "
        f"each to validator_jobs (covered) or grandfathered_validators (deferred)"
    )
    stale = union - applicable
    assert not stale, (
        f"validator_jobs/grandfathered_validators reference validators that are "
        f"not ci_workflow:required for {PILOT_REPO}: {sorted(stale)}"
    )


def test_spdx_headers_is_wired_not_grandfathered(spec: dict[str, Any]) -> None:
    """OMN-13576: spdx-headers graduated from grandfathered → validator_jobs.

    Locks the burn-down: spdx-headers must be a covered rollup validator (its CI
    job feeds quality-gate → CI Summary) and must NOT be listed as a deferred
    grandfathered gap. A revert that re-grandfathers spdx-headers turns this red.
    """
    cfg = spec["model_b_rollup_enforcement"]["repos"][PILOT_REPO]
    assert "spdx-headers" in cfg["validator_jobs"], (
        "spdx-headers must be covered in validator_jobs (OMN-13576 wiring)"
    )
    assert "spdx-headers" not in cfg.get("grandfathered_validators", []), (
        "spdx-headers must NOT be grandfathered — it is now a wired CI gate"
    )
    assert cfg["validator_jobs"]["spdx-headers"] == ["spdx-headers"], (
        "spdx-headers must map to the 'spdx-headers' ci.yml job"
    )


def test_malformed_opt_in_raises_value_error(spec: dict[str, Any]) -> None:
    """CodeRabbit #4: malformed opt-in config must surface as a deterministic
    ValueError, never a raw KeyError/TypeError."""
    mutated = copy.deepcopy(spec)
    # Drop a required key from the pilot opt-in.
    del mutated["model_b_rollup_enforcement"]["repos"][PILOT_REPO]["rollup_job"]
    verifier = RollupCoverageVerifier(mutated)
    with pytest.raises(ValueError, match="rollup_job"):
        verifier.verify_repo(repo_name=PILOT_REPO, repo_root=REPO_ROOT)

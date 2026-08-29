# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-16625: markdown-only diffs skip heavy CI (quality-gate leaves).

Operator ruling (verbatim): "Changes to markdown files should not trigger CI
except for the length validator." "The length validator" is the existing
`doc-content-scan` job today (stand-in for the not-yet-merged OMN-16589
kb-doc-gate) -- it and the 9 other `SPEC_REQUIRED_VALIDATOR_JOBS` members
(scripts/ci/ci_summary_gate.py) must keep running to strict success on every
diff, docs-only or not.

Before this ticket, `zone-filter` (the existing docs-only detector,
scripts/zone_diff_filter.py) ran AFTER `quality-gate`'s ~26 leaf validator
jobs (`needs: [quality-gate]`) -- too late in the DAG to gate those leaves on
`docs_only`. Only the Phase 2 test-execution matrix (`test-parallel`,
`detect-changes`, and transitively `tests-integration`/`shadow-compare`) was
already gated, via `tests-gate`'s existing OMN-15315 per-upstream skip
policy.

This ticket:
  1. Detaches `zone-filter` from `needs: [quality-gate]` so `docs_only` is
     known immediately, in parallel with quality-gate's leaves.
  2. Gates the 16 NON-spec-required quality-gate leaves on `docs_only` via
     `needs: [zone-filter]` + `if: always() && needs.zone-filter.outputs.docs_only != 'true'`.
  3. Rewrites `quality-gate`'s own bash aggregation into the same
     skip-tolerant per-check-loop shape `tests-gate` already uses: `quality-gate`
     itself stays `if: always()` (never itself a skip-vector) and re-derives
     `docs_only` from `needs.zone-filter.outputs.docs_only` before ever
     admitting a leaf's `skipped` conclusion as passing -- a skip on a
     non-docs-only diff still fails `quality-gate` closed.
  4. Leaves `contract-compliance`, `boundary-validation`, and
     `occ-companion-merged` fully untouched -- `contract-compliance`'s own
     in-file comment documents a PREVIOUSLY REJECTED attempt to narrow its
     `if:` (blocked by the `reject-required-check-skip-vector` guard,
     OMN-14863) because it is a direct, unwrapped `GATE_JOBS` entry with no
     re-deriving aggregator; building that safe wrapper is separable
     follow-up scope, not bundled here.

Fail-closed proof is structural: `quality-gate` is a `GATE_JOBS` completeness
anchor in `ci_summary_gate.py` (must be present+completed+success|skipped),
so a `quality-gate` failure fails `CI Summary` (the sole required
branch-protection context on `dev`, verified live via `gh api graphql`)
closed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
MANIFEST_PATH = REPO_ROOT / ".github" / "required-checks.yaml"

DOCS_ONLY_IF = "always() && needs.zone-filter.outputs.docs_only != 'true'"

# The 16 quality-gate leaves this ticket gates on docs_only -- everything in
# quality-gate's `needs:` list except the 10 SPEC_REQUIRED_VALIDATOR_JOBS
# members (see _STRICT_SPEC_REQUIRED_LEAVES below).
_DOCS_ONLY_GATED_LEAVES = (
    "pyright",
    "exports-validation",
    "lint-imports",
    "check-deterministic-skills",
    "docs-validation",
    "node-purity-check",
    "detect-secrets",
    "sdk-boundary-check",
    "contract-config-compliance",
    "breaking-schema-change",
    "no-env-fallbacks",
    "demo-path-topic-coherence",
    "dispatch-surface-test-required",
    "no-noncanonical-lifecycle-classes",
    "pydantic-extra-forbid",
    "pull-request-workflow-ratchet",
)

# scripts/ci/ci_summary_gate.py SPEC_REQUIRED_VALIDATOR_JOBS members that are
# ALSO quality-gate leaves (job KEY, not the ci_summary_gate.py job NAME).
# These must stay unconditional and strictly-success on every diff, docs-only
# included -- validator-requirements.yaml governs them, and changing that
# spec is explicitly out of this ticket's scope.
_STRICT_SPEC_REQUIRED_LEAVES = (
    "lint",
    "mypy-validation-scripts",
    "core-infra-boundary",
    "enum-governance",
    "naming-conventions",
    "pydantic-patterns",
    "aislop-patterns",
    "doc-content-scan",
    "no-new-os-environ",
    "spdx-headers",
)

# Manifest job_path values among the 16 gated leaves that carry a
# `mode: REQUIRED` row in required-checks.yaml (4 of the 16 -- lint-imports,
# no-noncanonical-lifecycle-classes, pydantic-extra-forbid,
# pull-request-workflow-ratchet -- were already removed/never added, per the
# manifest's own 2026-07-25 reconcile note, and need no row update).
_GATED_LEAVES_WITH_MANIFEST_ROWS = (
    "pyright",
    "exports-validation",
    "check-deterministic-skills",
    "docs-validation",
    "node-purity-check",
    "detect-secrets",
    "sdk-boundary-check",
    "contract-config-compliance",
    "breaking-schema-change",
    "no-env-fallbacks",
    "demo-path-topic-coherence",
    "dispatch-surface-test-required",
)


def _ci_workflow() -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _ci_job(name: str) -> dict[str, object]:
    jobs = _ci_workflow()["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _quality_gate_run_script() -> str:
    steps = _ci_job("quality-gate")["steps"]
    assert isinstance(steps, list)
    run = steps[0]["run"]
    assert isinstance(run, str)
    return run


def _manifest_gates() -> list[dict[str, object]]:
    data = yaml.safe_load(MANIFEST_PATH.read_text())
    gates = data["gates"]
    assert isinstance(gates, list)
    return gates


def _manifest_row_for_job_path(job_id: str) -> dict[str, object]:
    for gate in _manifest_gates():
        if gate.get("job_path") == [job_id]:
            return gate
    raise AssertionError(f"no required-checks.yaml row with job_path == [{job_id!r}]")


class TestZoneFilterIsDetachedAndAlwaysTrue:
    """zone-filter must compute docs_only immediately, not after
    quality-gate's leaves -- otherwise those leaves cannot gate on it."""

    def test_zone_filter_has_no_needs(self) -> None:
        job = _ci_job("zone-filter")
        assert "needs" not in job or not job["needs"]

    def test_zone_filter_if_is_provably_always_true(self) -> None:
        job = _ci_job("zone-filter")
        assert str(job["if"]).strip() == "always()"

    def test_zone_filter_no_longer_depends_on_quality_gate_result(self) -> None:
        """RED-before control: the pre-OMN-16625 shape gated zone-filter's
        own `if:` on `needs.quality-gate.result == 'success'` -- pin that
        the live condition has moved past it."""
        pre_gate_if = "always() && needs.quality-gate.result == 'success'"
        live_if = str(_ci_job("zone-filter")["if"]).strip()
        assert live_if != pre_gate_if
        assert "quality-gate" not in live_if


class TestDocsOnlyGatedLeaves:
    @pytest.mark.parametrize("job_id", _DOCS_ONLY_GATED_LEAVES)
    def test_leaf_needs_zone_filter(self, job_id: str) -> None:
        job = _ci_job(job_id)
        needs = job.get("needs")
        assert needs == ["zone-filter"], f"{job_id}: needs={needs!r}"

    @pytest.mark.parametrize("job_id", _DOCS_ONLY_GATED_LEAVES)
    def test_leaf_if_gates_on_docs_only(self, job_id: str) -> None:
        job = _ci_job(job_id)
        condition = str(job["if"]).strip()
        assert condition == DOCS_ONLY_IF, f"{job_id}: if={condition!r}"

    @pytest.mark.parametrize("job_id", _DOCS_ONLY_GATED_LEAVES)
    def test_leaf_is_not_a_spec_required_validator(self, job_id: str) -> None:
        """A gated leaf must never overlap the strict spec-required set --
        that would silently let a spec-required validator skip."""
        assert job_id not in _STRICT_SPEC_REQUIRED_LEAVES


class TestStrictSpecRequiredLeavesStayUnconditional:
    """The 10 SPEC_REQUIRED_VALIDATOR_JOBS members must run to STRICT
    success on every diff, including docs-only -- this is "the length
    validator" carve-out from the operator's ruling."""

    @pytest.mark.parametrize("job_id", _STRICT_SPEC_REQUIRED_LEAVES)
    def test_leaf_has_no_docs_only_if(self, job_id: str) -> None:
        job = _ci_job(job_id)
        condition = str(job.get("if", ""))
        assert "docs_only" not in condition, (
            f"{job_id} is spec-required (validator-requirements.yaml) and must "
            "run unconditionally -- it must never gate on docs_only"
        )

    @pytest.mark.parametrize("job_id", _STRICT_SPEC_REQUIRED_LEAVES)
    def test_leaf_does_not_need_zone_filter(self, job_id: str) -> None:
        job = _ci_job(job_id)
        needs = job.get("needs")
        if needs:
            assert isinstance(needs, list)
            assert "zone-filter" not in needs, (
                f"{job_id} is spec-required and must not depend on zone-filter"
            )

    def test_doc_content_scan_is_the_carved_out_length_validator(self) -> None:
        """Explicit single-job pin for the operator's exact carve-out
        phrase ("the length validator") -- doc-content-scan is its current
        stand-in until OMN-16589's kb-doc-gate lands."""
        job = _ci_job("doc-content-scan")
        assert "if" not in job
        assert "needs" not in job or not job["needs"]


class TestQualityGateAggregatorReDerivesDocsOnly:
    def test_quality_gate_itself_stays_unconditional(self) -> None:
        """quality-gate must never itself be a skip-vector -- it always
        runs and always produces a real success/failure, mirroring
        tests-gate."""
        assert str(_ci_job("quality-gate")["if"]).strip() == "always()"

    def test_quality_gate_needs_zone_filter(self) -> None:
        needs = _ci_job("quality-gate")["needs"]
        assert isinstance(needs, list)
        assert "zone-filter" in needs

    def test_quality_gate_needs_every_gated_leaf_and_every_strict_leaf(self) -> None:
        raw_needs = _ci_job("quality-gate")["needs"]
        assert isinstance(raw_needs, list)
        needs = set(raw_needs)
        for job_id in _DOCS_ONLY_GATED_LEAVES + _STRICT_SPEC_REQUIRED_LEAVES:
            assert job_id in needs, f"quality-gate no longer needs {job_id!r}"

    def test_step_reads_docs_only_from_zone_filter_output(self) -> None:
        script = _quality_gate_run_script()
        assert 'docs_only="${{ needs.zone-filter.outputs.docs_only }}"' in script, (
            "quality-gate must re-derive docs_only from zone-filter's own output"
        )

    def test_step_never_trusts_zone_filter_result_directly(self) -> None:
        """Only the `docs_only` OUTPUT may be read -- never
        `needs.zone-filter.result` (that would be trusting the detector
        job's own conclusion instead of its computed verdict, which is not
        the same thing zone-filter's own `if: always()` makes it -- a
        successful run always concludes 'success' regardless of docs_only)."""
        script = _quality_gate_run_script()
        assert "needs.zone-filter.result" not in script

    @pytest.mark.parametrize("job_id", _STRICT_SPEC_REQUIRED_LEAVES)
    def test_strict_leaf_var_is_checked_in_the_strict_tier(self, job_id: str) -> None:
        script = _quality_gate_run_script()
        tier1, _, _tier2 = script.partition("TIER 2")
        assert job_id.replace("-", "_") in tier1 or _var_alias(job_id) in tier1

    def test_skip_is_admitted_only_when_docs_only_true(self) -> None:
        script = _quality_gate_run_script()
        assert 'case "$RESULT" in' in script
        assert "skipped)" in script
        assert '"$docs_only" != "true"' in script

    def test_a_skip_on_a_non_docs_only_diff_fails_the_gate(self) -> None:
        """Structural proof the skip-tolerant loop fails closed: the
        `skipped)` branch's guard clause is followed by an `exit 1`."""
        script = _quality_gate_run_script()
        skipped_branch = script.split("skipped)", 1)[1].split("failure|cancelled", 1)[0]
        assert "exit 1" in skipped_branch
        assert '"$docs_only" != "true"' in skipped_branch


# Job keys use hyphens; the bash variable names quality-gate's step assigns
# for the 10 strict leaves are hand-abbreviated, not a mechanical
# hyphen->underscore transform (matching the pre-existing style already in
# the step for the other ~40 vars) -- map the two that diverge.
_STRICT_VAR_ALIASES = {
    "mypy-validation-scripts": "mypy_scripts",
    "core-infra-boundary": "core_infra",
    "enum-governance": "enum_gov",
    "naming-conventions": "naming",
    "pydantic-patterns": "pydantic",
    "aislop-patterns": "aislop",
    "doc-content-scan": "doc_content",
    "no-new-os-environ": "no_new_os_environ",
}


def _var_alias(job_id: str) -> str:
    return _STRICT_VAR_ALIASES.get(job_id, job_id.replace("-", "_"))


class TestDeliberatelyUntouchedJobs:
    """contract-compliance / boundary-validation / occ-companion-merged are
    direct, unwrapped GATE_JOBS entries with no re-deriving aggregator (see
    module docstring) -- gating them here would repeat a PREVIOUSLY REJECTED
    change (see contract-compliance's own in-file comment, OMN-14863)."""

    def test_contract_compliance_if_does_not_reference_docs_only(self) -> None:
        condition = str(_ci_job("contract-compliance").get("if", ""))
        assert "docs_only" not in condition

    def test_boundary_validation_has_no_if_at_all(self) -> None:
        assert "if" not in _ci_job("boundary-validation")

    def test_occ_companion_merged_has_no_if_at_all(self) -> None:
        assert "if" not in _ci_job("occ-companion-merged")


class TestRequiredChecksManifestOverrides:
    @pytest.mark.parametrize("job_id", _GATED_LEAVES_WITH_MANIFEST_ROWS)
    def test_row_has_neutral_ok_with_ticket_cited_rationale(self, job_id: str) -> None:
        row = _manifest_row_for_job_path(job_id)
        assert row["skip_semantics"] == "neutral_ok"
        rationale = str(row["rationale"])
        assert re.search(r"\bOMN-\d+\b", rationale), (
            f"{job_id} row's rationale must cite a tracking ticket "
            "(validate_no_required_check_skip_vectors.py only honors "
            "neutral_ok with a cited ticket)"
        )
        assert "OMN-16625" in rationale

    def test_zone_filter_row_reverted_to_never_now_that_if_is_always_true(
        self,
    ) -> None:
        """zone-filter's `if:` is now provably ALWAYS_TRUE_FOR_PR (see
        TestZoneFilterIsDetachedAndAlwaysTrue) -- the neutral_ok override
        this row previously needed (OMN-14864) is no longer reachable."""
        row = _manifest_row_for_job_path("zone-filter")
        assert row["skip_semantics"] == "never"

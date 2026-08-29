# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-16215: draft-state CI admission gate on omnibase_core.

Org-wide fan-out (OMN-16214) of the draft-state CI admission-gate mechanism
proven on onex_change_control#6686 (OMN-15731). Operator: "we had a label
gate -- that should be implemented everywhere."

Unlike OCC, this repo has no existing `ci:ready` label pilot to fold into a
dual-accept arm -- this is a pure draft-state gate (verified against the live
workflow file before building: no job in ci.yml referenced `ci:ready` prior
to this change).

Scoping decision (see the PR body for the full table): OCC's mechanism gated
ONE monolithic `pre-commit` job that did all its heavy lifting in one shot.
omnibase_core has no equivalent single job -- `quality-gate` fans out into
~50 single-shard leaf jobs that already run on cheap `ubuntu-latest` runners
for `pull_request` events (verified live: the `OMNI_RUNNER_SELECTOR_V1`
`runs-on` conditional routes every `pull_request`-triggered job, including
`test-parallel`/`tests-integration`, to `ubuntu-latest` -- self-hosted is
push/merge_group only). The two jobs gated here (`test-parallel`,
`tests-integration`) are the highest-leverage targets: `test-parallel` fans
out to up to 40 shards at up to 70m each, `tests-integration` to 4 shards at
up to 30m each -- together the overwhelming majority of this workflow's
runner-minutes and wall-clock, regardless of which runner pool serves them.
The ~50 quality-gate leaves are left ungated BY THIS TICKET (OMN-16215):
each is a single-shard job completing in a few minutes, each was already
required at STRICT (not skip-tolerant) success, and touching 50 independent
`if:` clauses individually for comparatively small marginal savings was a
large blast-radius change this ticket's scoping guidance ("minimal always-on
set") argued against for the DRAFT-state gate specifically.

Update (OMN-16625): a separate, later ticket DID subsequently gate 16 of
these leaves -- but on `docs_only`, not on draft state, and via the
tests-gate-style skip-tolerant re-deriving pattern, not a bare `if:`. The
`_UNGATED_QUALITY_GATE_LEAF_SAMPLE` assertions below only pin the absence of
"draft" in each leaf's `if:` condition, so they remain true and unchanged --
this note exists so a reader doesn't conclude from the sample name that these
jobs still have no `if:` at all.

Fail-closed proof is structural, not new code: `test-parallel`/
`tests-integration` feed `Tests Gate` (`tests-gate` job), whose existing
OMN-15315 per-upstream skip policy already treats a `skipped` result as a
FAILURE unless `zone-filter`'s `docs_only` output is `'true'` -- a draft,
non-docs-only PR gets `Tests Gate: FAILED`, not skip-green. `Tests Gate` is
itself a `GATE_JOBS` completeness anchor in `ci_summary_gate.py`, so a
failure there fails `CI Summary` (the sole required branch-protection
context) closed. No change to `tests-gate`'s bash logic or to
`ci_summary_gate.py` was needed or made.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"

_GATED_JOB_IDS = ("test-parallel", "tests-integration")

# Leaf jobs under `quality-gate` that this ticket deliberately leaves
# ungated -- see the module docstring's scoping decision. A sample, not the
# full ~50-job set: enough to pin the "leaves are untouched" invariant
# without hand-maintaining the complete list here (which would drift
# independently of quality-gate's own `needs:` list).
_UNGATED_QUALITY_GATE_LEAF_SAMPLE = (
    "lint",
    "pyright",
    "mypy-validation-scripts",
    "naming-conventions",
    "detect-secrets",
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


class TestPullRequestTriggerCoversDraftToReadyFlip:
    def test_ready_for_review_is_a_pull_request_trigger_type(self) -> None:
        """A draft->ready flip must re-evaluate the gate on the current head
        without requiring a new push."""
        workflow = _ci_workflow()
        pr_trigger = workflow[True]["pull_request"]
        assert isinstance(pr_trigger, dict)
        assert "ready_for_review" in pr_trigger["types"]

    def test_default_trigger_types_are_preserved(self) -> None:
        """The explicit `types:` list must not silently drop a default type
        GitHub would otherwise have implied (opened/synchronize/reopened)."""
        workflow = _ci_workflow()
        pr_trigger = workflow[True]["pull_request"]
        assert isinstance(pr_trigger, dict)
        for event_type in ("opened", "synchronize", "reopened"):
            assert event_type in pr_trigger["types"]


@pytest.mark.parametrize("job_id", _GATED_JOB_IDS)
class TestDraftStateAdmissionGate:
    def test_draft_arm_is_present(self, job_id: str) -> None:
        condition = str(_ci_job(job_id)["if"])
        assert "!github.event.pull_request.draft" in condition

    def test_main_boundary_carveout_survives_the_gate(self, job_id: str) -> None:
        """The dev->main promotion-boundary guarantee (root CLAUDE.md rule
        #4) must be untouched: main-targeting PRs always run this job
        unconditionally, draft or not."""
        condition = str(_ci_job(job_id)["if"])
        assert "github.base_ref != 'dev'" in condition

    def test_non_pull_request_events_are_exempted(self, job_id: str) -> None:
        """push/merge_group/workflow_dispatch runs have no PR draft state at
        all -- the gate must not evaluate `.draft` against a non-existent
        `pull_request` object."""
        condition = str(_ci_job(job_id)["if"])
        assert "github.event_name != 'pull_request'" in condition

    def test_preexisting_preconditions_are_unchanged(self, job_id: str) -> None:
        """This ticket ONLY adds an admission arm -- it must not touch the
        job's existing quality-gate/docs_only preconditions."""
        condition = str(_ci_job(job_id)["if"])
        assert "needs.quality-gate.result == 'success'" in condition
        assert "needs.zone-filter.outputs.docs_only != 'true'" in condition

    def test_no_ci_ready_label_fallback_arm(self, job_id: str) -> None:
        """Core has no pre-existing label pilot for this job (verified
        against the live workflow file before building) -- this is a pure
        draft-state gate, not OCC's dual-accept migration. Do not add a
        `ci:ready` arm here without a matching ticket."""
        condition = str(_ci_job(job_id)["if"])
        assert "ci:ready" not in condition

    def test_red_control_pre_gate_shape_had_no_draft_arm(self, job_id: str) -> None:
        """RED-before control: the pre-OMN-16215 condition string for both
        gated jobs was identical and referenced neither draft state nor a
        base_ref carve-out -- a draft PR with a real (non-docs-only) code
        change was previously ADMITTED to the full test matrix purely
        because `always()` held. This pins that pre-migration string so a
        future revert is caught by drift, not by eyeballing history."""
        pre_gate_condition = (
            "always() && needs.quality-gate.result == 'success' && "
            "needs.zone-filter.outputs.docs_only != 'true'"
        )
        assert "!github.event.pull_request.draft" not in pre_gate_condition
        live_condition = str(_ci_job(job_id)["if"])
        assert live_condition != pre_gate_condition, (
            f"{job_id}: live ci.yml condition must have moved past the "
            "pre-gate shape captured above"
        )


class TestUngatedScopeIsUnchanged:
    """Scope-lock: this ticket touches exactly two jobs' `if:` conditions
    plus the pull_request trigger `types:`. Everything else in ci.yml --
    including detect-changes (cheap, feeds test-parallel's matrix but is not
    itself expensive) and every quality-gate leaf -- must remain untouched by
    the draft-state gate."""

    @pytest.mark.parametrize("job_id", _UNGATED_QUALITY_GATE_LEAF_SAMPLE)
    def test_quality_gate_leaf_sample_is_not_draft_gated(self, job_id: str) -> None:
        job = _ci_job(job_id)
        condition = str(job.get("if", ""))
        assert "draft" not in condition, (
            f"{job_id} is a quality-gate leaf deliberately left ungated by "
            "OMN-16215 -- see the module docstring's scoping decision"
        )

    def test_detect_changes_is_not_draft_gated(self) -> None:
        condition = str(_ci_job("detect-changes")["if"])
        assert "draft" not in condition

    def test_quality_gate_aggregator_itself_is_not_draft_gated(self) -> None:
        """quality-gate's own `if: always()` must stay unconditional -- its
        leaves already run regardless of draft state (see the module
        docstring), so gating the aggregator without gating the leaves would
        misrepresent what actually ran."""
        condition = str(_ci_job("quality-gate")["if"])
        assert condition.strip() == "always()"

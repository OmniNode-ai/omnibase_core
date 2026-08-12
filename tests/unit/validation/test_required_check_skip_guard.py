# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[3]
ACTION_DIR = REPO_ROOT / ".github" / "actions" / "required-check-skip-guard"
MANIFEST_PATH = REPO_ROOT / ".github" / "required-checks.yaml"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

pytestmark = pytest.mark.unit


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


workflow_model = _load_module(
    "required_check_skip_guard_model", ACTION_DIR / "_workflow_model.py"
)
sys.modules["_workflow_model"] = workflow_model
validator = _load_module(
    "required_check_skip_guard_validator",
    ACTION_DIR / "validate_no_required_check_skip_vectors.py",
)


def test_classifier_rejects_expression_requiring_code_execution() -> None:
    verdict = workflow_model.classify(
        "github.event_name == 'pull_request' or ().__class__.__bases__[0].__subclasses__()",
        ("pull_request",),
    )

    assert verdict == workflow_model.UNGUARDED_CONDITIONAL


def test_neutral_ok_requires_ticket_citation() -> None:
    job = workflow_model.ParsedJob(
        job_id="gate",
        raw={"if": "always() && needs.quality-gate.result == 'success'"},
    )
    workflow = workflow_model.ParsedWorkflow(
        path=Path("ci.yml"),
        raw={"on": ["pull_request"], "jobs": {"gate": job.raw}},
    )

    findings_without_ticket = validator._check_job_if(
        "gate",
        workflow,
        job,
        "producing job",
        "vector-2-ungated-job-if",
        skip_semantics="neutral_ok",
        rationale="reviewed exception",
    )
    findings_with_ticket = validator._check_job_if(
        "gate",
        workflow,
        job,
        "producing job",
        "vector-2-ungated-job-if",
        skip_semantics="neutral_ok",
        rationale="reviewed exception in OMN-14864",
    )

    assert findings_without_ticket
    assert findings_with_ticket == []


def test_cross_repo_unresolved_context_fails_closed() -> None:
    findings = validator.validate_gate(
        "missing / external",
        {"producer_kind": "cross_repo"},
        {},
    )

    assert [finding.vector for finding in findings] == ["vector-unresolved"]


def test_no_required_caller_job_has_ungated_top_level_if() -> None:
    """Regression guard (OMN-15120/OMN-14864).

    A required context's CALLER job — the job in this repo's own workflow
    file that does `uses: <reusable>.yml` and produces the composed
    "<caller-job> / <reusable-job-name>" context string — must never carry a
    top-level `if:` that can evaluate false on an ordinary PR/merge_group
    event. If the CALLER job is skipped, GitHub never invokes the reusable
    workflow at all, so no check run is ever created under the composed
    context name: the required check goes PENDING forever, it does not pass.
    This is distinct from (and strictly worse than) a job-level `if:` INSIDE
    an already-invoked reusable, which still posts a real "skipped"
    conclusion that GitHub branch protection accepts as passing.

    Live case this guards against: omnibase_core#1548 (a Dependabot PR) could
    never merge because "gate / CodeRabbit Thread Check" and
    "occ-companion-effect / Publish occ-companion-effect command" both had an
    ungated caller-level `if:` excluding `github.actor == 'dependabot[bot]'`.
    See docs/diagnoses/2026-08-06-omnibase-core-1548-missing-required-contexts.md.

    Deliberately does NOT honor `skip_semantics: neutral_ok` from
    required-checks.yaml — unlike the shared skip-vector guard script
    (validate_no_required_check_skip_vectors.py), which currently lets
    neutral_ok suppress this exact class of finding (the manifest drift the
    diagnosis identifies). A caller-level skip is never semantically neutral:
    it suppresses check-run creation outright, so there is no legitimate
    ratified exception for it. If a future gate legitimately needs a
    caller-level `if:`, eligibility belongs inside the executed producer
    (the reusable's own job), not on the caller.
    """
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    workflows = workflow_model.load_workflows(WORKFLOWS_DIR)

    violations: list[str] = []
    for gate in manifest.get("gates", []):
        if gate.get("mode") != "REQUIRED":
            continue
        context = gate["name"]
        try:
            resolved = workflow_model.resolve_context_to_job(context, workflows)
        except workflow_model.UnresolvedContext:
            # Manifest/workflow drift is covered separately by
            # validate_no_required_check_skip_vectors.py's vector-unresolved
            # finding; not this guard's concern.
            continue

        if resolved.caller_job_id is None:
            # Shape A: the producing job IS the context (no `uses:` wrapper),
            # so there is no separate caller-level `if:` to suppress check-run
            # creation. A job-level `if:` here still produces a "skipped"
            # check run and is validated separately (vector-2).
            continue

        caller_wf = resolved.workflow
        caller_job = caller_wf.jobs[resolved.caller_job_id]
        declared_events = validator._declared_events(caller_wf)
        verdict = workflow_model.classify(caller_job.if_expr, declared_events)
        if verdict != workflow_model.ALWAYS_TRUE_FOR_PR:
            violations.append(
                f"{context!r}: caller job '{caller_job.job_id}' in "
                f"{caller_wf.path.name} has `if: {caller_job.if_expr}` — a "
                "skipped caller job produces NO check run under this composed "
                "context name, wedging the required check PENDING forever. "
                "Move actor/ticket eligibility inside the executed producer "
                "(the reusable's own job) instead."
            )

    assert not violations, "\n".join(violations)


def _is_bare_always(if_expr: str | None) -> bool:
    """True when `if_expr` is exactly `always()`, bare or `${{ }}`-wrapped."""
    normalized = (if_expr or "").strip()
    if normalized.startswith("${{") and normalized.endswith("}}"):
        normalized = normalized[3:-2].strip()
    return normalized == "always()"


def test_no_required_job_has_ungated_needs_cascade() -> None:
    """Regression guard (OMN-15120/OMN-14864, second vector on the same tickets).

    A required context's producing job — whether it IS the context (Shape A)
    or is the CALLER job that wraps a reusable producing a composed context
    (Shape B/C) — must never declare `needs:` without pairing it with
    `if: always()`. GitHub's default behavior implicitly skips a job when any
    job it `needs:` fails or is skipped, with NO explicit `if:` required to
    trigger that skip. For a Shape A job this still produces a check run
    (conclusion=skipped, which branch protection accepts) — but for a Shape
    B/C CALLER job it reproduces the exact vector-3 failure from
    test_no_required_caller_job_has_ungated_top_level_if above: the reusable
    is never invoked, so the composed check run never exists at all, and the
    required check is PENDING forever.

    `occ-preflight` failing (the common `needs:` target across this repo's
    required callers) is the ORDINARY state of any fresh non-exempt PR before
    its OCC companion is minted — not Dependabot-specific. Two live instances
    were found on this repair's own verification PR (omnibase_core#1549):

    - `gate` in cr-thread-gate-caller.yml (CodeRabbit finding, confirmed via
      check-run inspection: job 92915155222 showed the bare name "gate",
      conclusion=skipped, no composed "gate / CodeRabbit Thread Check" run,
      on a run where occ-preflight had failed).
    - `codeql` in security-scan.yml, matching the manifest's own pre-existing
      "vector-5 (ungated needs cascade)" note on the "CodeQL" gate, which
      named this exact ticket pairing as the pending triage. This job
      resolves Shape A on its OWN bare name ("CodeQL"), which a needs-skip
      wouldn't itself endanger (a Shape A skip still posts a real
      "skipped" check run) — but the job also has `uses:`, and the manifest
      separately lists "CodeQL / CodeQL Analysis (python)" (the reusable's
      OWN composed context) as REQUIRED too; that composed context can only
      ever materialize if this job actually invokes the reusable.

    Every other required `needs: occ-preflight` caller in this repo already
    pairs it with `if: always()` (deploy-gate.yml, pr-title-check.yml,
    required-check-skip-guard-caller.yml, call-receipt-gate.yml) — this test
    makes that convention mechanically enforced instead of merely observed.

    Scoped to jobs that themselves carry a `uses:` (invoke a reusable
    workflow) — a plain local job (no `uses:`) that gets needs-cascade
    skipped still posts its OWN check run with conclusion=skipped, which
    satisfies branch protection directly; there is no reusable-invocation
    boundary for the skip to hide behind, so no vector-3 danger exists for
    it (e.g. ci.yml's `zone-filter`, omni-standards-compliance.yml's
    `ecosystem-validation` — deliberately excluded, not oversights).
    """
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    workflows = workflow_model.load_workflows(WORKFLOWS_DIR)

    violations: list[str] = []
    for gate in manifest.get("gates", []):
        if gate.get("mode") != "REQUIRED":
            continue
        context = gate["name"]
        try:
            resolved = workflow_model.resolve_context_to_job(context, workflows)
        except workflow_model.UnresolvedContext:
            continue

        job = resolved.workflow.jobs[resolved.job_id]
        if job.uses is None:
            # No reusable-invocation boundary — a needs-cascade skip here
            # still produces this job's own "skipped" check run, which
            # satisfies branch protection directly. Nothing to guard.
            continue
        needs = job.raw.get("needs")
        if not needs:
            continue
        if _is_bare_always(job.if_expr):
            continue

        violations.append(
            f"{context!r}: job '{job.job_id}' in {resolved.workflow.path.name} "
            f"has `needs: {needs!r}` but `if: {job.if_expr!r}` is not "
            "`always()` — GitHub's default implicit-skip-on-failed-need "
            "behavior means this job (and, if it wraps a reusable via "
            "`uses:`, the composed check-run under it) goes missing entirely "
            "whenever any needed job fails or is skipped, with no explicit "
            "conditional required to trigger it."
        )

    assert not violations, "\n".join(violations)

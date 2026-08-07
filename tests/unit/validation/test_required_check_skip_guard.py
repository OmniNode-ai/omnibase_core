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

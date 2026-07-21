# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ACTION_DIR = (
    Path(__file__).parents[3] / ".github" / "actions" / "required-check-skip-guard"
)


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

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the repository-specific CI job handler (OMN-17427).

RULING 2026-10-14T19:54:41Z: repositories of the same type run exactly the
same CI. RULING 2026-10-14T20:01:09Z: that CI lives in omnibase_core and every
repository inherits it. The handler refuses a change that ADDS a job defined
inline in a repository's own workflow, unless the repository is the host and
the workflow is a reusable one (``on: workflow_call``) every repository can
call. A job that calls a reusable workflow (``uses:``) is not judged here: the
ci-inheritance handler judges where its callee is hosted. Inline jobs the base
already carries are reported as one WARN per file, never FAIL.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_ci_repository_jobs_check_compute.handler_ci_repository_jobs import (
    HandlerCiRepositoryJobs,
)

pytestmark = pytest.mark.unit

_CI = """\
name: CI
on:
  pull_request:
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check
"""

_NEW_INLINE_JOB = """\
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - run: mypy
"""

_CORE_CALL_JOB = """\
  gate:
    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@abc123
"""

_REUSABLE = """\
name: Shared lint
on:
  workflow_call:
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check
"""


def _request(
    base: dict[str, str],
    head: dict[str, str],
    repository: str | None = None,
) -> ModelCiInheritanceCheckInput:
    return ModelCiInheritanceCheckInput(
        organization="OmniNode-ai",
        host_repository="omnibase_core",
        repository=repository,
        base_files=[ModelSourceFile(path=p, source=s) for p, s in base.items()],
        head_files=[ModelSourceFile(path=p, source=s) for p, s in head.items()],
    )


def _fails(report_findings: tuple[object, ...]) -> list[object]:
    return [f for f in report_findings if getattr(f, "severity", None) == "FAIL"]


def test_added_inline_job_in_host_ci_fails() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({"ci.yml": _CI}, {"ci.yml": _CI + _NEW_INLINE_JOB})
    )
    assert report.overall_status == "FAIL"
    fails = _fails(report.findings)
    assert len(fails) == 1
    assert fails[0].location == "ci.yml:jobs.typecheck"
    assert "typecheck" in fails[0].message
    assert fails[0].remediation is not None
    assert "2026-10-14T19:54:41Z" in fails[0].remediation


def test_added_inline_job_in_host_reusable_workflow_passes() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({}, {"lint-reusable.yml": _REUSABLE})
    )
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_reusable_with_other_triggers_is_still_shared() -> None:
    mapping = _REUSABLE.replace(
        "on:\n  workflow_call:\n", "on:\n  pull_request:\n  workflow_call:\n"
    )
    listed = _REUSABLE.replace("on:\n  workflow_call:\n", "on: [push, workflow_call]\n")
    scalar = _REUSABLE.replace("on:\n  workflow_call:\n", "on: workflow_call\n")
    for source in (mapping, listed, scalar):
        report = HandlerCiRepositoryJobs().handle(_request({}, {"r.yml": source}))
        assert report.overall_status == "PASS", source


def test_added_job_that_calls_a_reusable_workflow_is_not_judged() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({"ci.yml": _CI}, {"ci.yml": _CI + _CORE_CALL_JOB})
    )
    assert _fails(report.findings) == []


def test_existing_inline_jobs_are_one_warn_per_file() -> None:
    two_jobs = _CI + _NEW_INLINE_JOB
    report = HandlerCiRepositoryJobs().handle(
        _request({"ci.yml": two_jobs}, {"ci.yml": two_jobs})
    )
    assert report.overall_status == "WARN"
    assert [f.severity for f in report.findings] == ["WARN"]
    assert "2 existing repository-specific job(s)" in report.findings[0].message


def test_step_change_inside_existing_job_is_not_new() -> None:
    changed = _CI.replace("ruff check", "ruff check --fix")
    report = HandlerCiRepositoryJobs().handle(
        _request({"ci.yml": _CI}, {"ci.yml": changed})
    )
    assert _fails(report.findings) == []


def test_removed_job_passes() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({"ci.yml": _CI + _NEW_INLINE_JOB}, {"ci.yml": _CI})
    )
    assert _fails(report.findings) == []


def test_non_host_reusable_workflow_is_repository_specific() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({}, {"lint-reusable.yml": _REUSABLE}, repository="omnibase_spi")
    )
    assert report.overall_status == "FAIL"
    assert [f.location for f in _fails(report.findings)] == [
        "lint-reusable.yml:jobs.lint"
    ]


def test_non_host_call_into_core_passes() -> None:
    caller = "name: CI\non:\n  pull_request:\njobs:\n" + _CORE_CALL_JOB
    report = HandlerCiRepositoryJobs().handle(
        _request({}, {"ci.yml": caller}, repository="omnibase_spi")
    )
    assert report.overall_status == "PASS"


def test_host_match_is_case_insensitive() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({}, {"r.yml": _REUSABLE}, repository="OmniBase_Core")
    )
    assert report.overall_status == "PASS"


def test_unparseable_head_workflow_is_error() -> None:
    report = HandlerCiRepositoryJobs().handle(_request({}, {"broken.yml": "jobs: [\n"}))
    assert report.overall_status == "ERROR"
    assert [f.location for f in report.findings] == ["broken.yml"]


def test_workflow_with_no_jobs_mapping_has_no_findings() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request({}, {"empty.yml": "name: nothing\n"})
    )
    assert report.findings == ()

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the shrink-only CI inheritance baseline (OMN-21277, AC1 and AC2).

RULING 2026-10-14T19:54:41Z: repositories of the same type run the same CI.
RULING 2026-10-14T20:01:09Z: that CI lives in omnibase_core and is inherited.
With a baseline, a typed repository's inline job passes only when the
baseline lists it, whatever the base carried; an entry the base baseline did
not list (a new or re-added entry) fails, and an entry naming no inline job
is stale and fails, so the list can only shrink.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_ci_repository_type import EnumCiRepositoryType
from omnibase_core.handlers.handler_ci_repository_jobs import (
    HandlerCiRepositoryJobs,
    repository_specific_jobs,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_baseline import (
    ModelCiInheritanceBaseline,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CORE_BASELINE = _REPO_ROOT / ".onex_ratchets" / "ci_inheritance_baseline.yaml"

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

_TYPECHECK = """\
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - run: mypy
"""


def _baseline(
    *entries: str, repository: str = "omnibase_spi"
) -> ModelCiInheritanceBaseline:
    return ModelCiInheritanceBaseline(
        repository=repository,
        repository_type=EnumCiRepositoryType.PYTHON,
        entries=entries,
    )


def _request(
    head: dict[str, str],
    baseline: ModelCiInheritanceBaseline,
    *,
    base: dict[str, str] | None = None,
    base_baseline: ModelCiInheritanceBaseline | None = None,
    compare_base: bool = True,
    repository: str = "omnibase_spi",
) -> ModelCiInheritanceCheckInput:
    return ModelCiInheritanceCheckInput(
        organization="OmniNode-ai",
        host_repository="omnibase_core",
        repository=repository,
        base_files=[ModelSourceFile(path=p, source=s) for p, s in (base or {}).items()],
        head_files=[ModelSourceFile(path=p, source=s) for p, s in head.items()],
        baseline=baseline,
        base_baseline=base_baseline,
        compare_base=compare_base,
    )


def _fail_locations(request: ModelCiInheritanceCheckInput) -> list[str]:
    report = HandlerCiRepositoryJobs().handle(request)
    return [f.location or "" for f in report.findings if f.severity == "FAIL"]


def test_unlisted_inline_job_fails_even_when_the_base_carried_it() -> None:
    """AC1: the base no longer excuses a job; only the baseline does."""
    head = {"ci.yml": _CI + _TYPECHECK}
    listed = _baseline("ci.yml:jobs.lint")
    request = _request(head, listed, base=head, base_baseline=listed)
    assert _fail_locations(request) == ["ci.yml:jobs.typecheck"]


def test_listed_inline_jobs_pass_as_one_warn_per_file() -> None:
    head = {"ci.yml": _CI + _TYPECHECK}
    listed = _baseline("ci.yml:jobs.lint", "ci.yml:jobs.typecheck")
    report = HandlerCiRepositoryJobs().handle(
        _request(head, listed, base=head, base_baseline=listed)
    )
    assert report.overall_status == "WARN"
    assert [f.severity for f in report.findings] == ["WARN"]
    assert "2 baselined repository-specific job(s)" in report.findings[0].message


def test_re_added_entry_fails() -> None:
    """AC1: an entry the base baseline dropped cannot come back."""
    head = {"ci.yml": _CI + _TYPECHECK}
    request = _request(
        head,
        _baseline("ci.yml:jobs.lint", "ci.yml:jobs.typecheck"),
        base={"ci.yml": _CI},
        base_baseline=_baseline("ci.yml:jobs.lint"),
    )
    report = HandlerCiRepositoryJobs().handle(request)
    fails = [f for f in report.findings if f.severity == "FAIL"]
    assert [f.location for f in fails] == ["baseline:ci.yml:jobs.typecheck"]
    assert "not in the base baseline" in fails[0].message


def test_stale_entry_fails() -> None:
    head = {"ci.yml": _CI}
    listed = _baseline("ci.yml:jobs.lint", "ci.yml:jobs.typecheck")
    request = _request(
        head, listed, base={"ci.yml": _CI + _TYPECHECK}, base_baseline=listed
    )
    assert _fail_locations(request) == ["baseline:ci.yml:jobs.typecheck"]


def test_first_baseline_lists_only_jobs_the_base_already_carried() -> None:
    """With no base baseline, an entry must name an inline job of the base."""
    head = {"ci.yml": _CI + _TYPECHECK}
    request = _request(
        head,
        _baseline("ci.yml:jobs.lint", "ci.yml:jobs.typecheck"),
        base={"ci.yml": _CI},
        base_baseline=None,
    )
    assert _fail_locations(request) == ["baseline:ci.yml:jobs.typecheck"]


def test_without_a_base_only_the_baseline_is_enforced() -> None:
    head = {"ci.yml": _CI + _TYPECHECK}
    request = _request(head, _baseline("ci.yml:jobs.lint"), compare_base=False)
    assert _fail_locations(request) == ["ci.yml:jobs.typecheck"]


def test_baseline_of_another_repository_is_error() -> None:
    report = HandlerCiRepositoryJobs().handle(
        _request(
            {"ci.yml": _CI}, _baseline("ci.yml:jobs.lint", repository="omniclaude")
        )
    )
    assert report.overall_status == "ERROR"


def test_duplicate_baseline_entry_is_refused() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _baseline("ci.yml:jobs.lint", "ci.yml:jobs.lint")


def test_empty_baseline_refuses_a_new_entry() -> None:
    """AC2 shape: an empty baseline plus a fixture entry fails."""
    head = {"ci.yml": _CI}
    request = _request(
        head,
        _baseline("ci.yml:jobs.lint"),
        base=head,
        base_baseline=_baseline(),
    )
    assert _fail_locations(request) == ["baseline:ci.yml:jobs.lint"]


def test_core_baseline_is_typed_and_matches_its_workflows() -> None:
    """The committed omnibase_core baseline lists exactly its inline jobs."""
    data = yaml.load(_CORE_BASELINE.read_text(), Loader=yaml.SafeLoader)
    baseline = ModelCiInheritanceBaseline.model_validate(data)
    assert baseline.repository == "omnibase_core"
    assert baseline.repository_type is EnumCiRepositoryType.PYTHON
    workflows = sorted((_REPO_ROOT / ".github" / "workflows").glob("*.y*ml"))
    jobs = {
        location
        for path in workflows
        for location in repository_specific_jobs(
            path.read_text(), path.name, "omnibase_core", "omnibase_core"
        )
    }
    assert set(baseline.entries) == jobs

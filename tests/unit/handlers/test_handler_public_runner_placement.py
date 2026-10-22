# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the public-repository runner placement check (OMN-19998, OMN-21280).

RULING 2026-10-16T07:07:09Z: "Ci runners should be for private repos only."
The negative controls are the FAIL cases: a public repository that carries a
self-hosted job must fail, with no baseline to excuse it (OMN-21280), and the
same job in a private repository must not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.handlers import handler_public_runner_placement_cli as cli
from omnibase_core.handlers.handler_public_runner_placement import (
    HandlerPublicRunnerPlacement,
    runs_on_kind,
    self_hosted_jobs,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.version_drift.model_public_runner_placement_input import (
    ModelPublicRunnerPlacementInput,
)

pytestmark = pytest.mark.unit

CI = ".github/workflows/ci.yml"
HOSTED = "ubuntu-latest"
LAB = "[self-hosted, omnibase-ci]"
COMPUTED = '${{ fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || \'["self-hosted","omnibase-ci"]\') }}'
PRIVATE_GUARDED = (
    "${{ github.event.repository.private && ("
    'fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || \'["self-hosted","omnibase-ci"]\')'
    ") || 'ubuntu-latest' }}"
)

# A public repository's workflow: every job but `lint`, `docs` and `routed` is
# or may resolve to a self-hosted runner, and none of them is excused.
FIXTURE_PUBLIC_WORKFLOW = f"""\
name: ci
on: [pull_request, push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps: [{{run: echo ok}}]
  docs:
    runs-on: [ubuntu-22.04]
    steps: [{{run: echo ok}}]
  routed:
    runs-on: {PRIVATE_GUARDED}
    steps: [{{run: echo ok}}]
  literal:
    runs-on: self-hosted
    steps: [{{run: echo ok}}]
  labels:
    runs-on: [self-hosted, omnibase-ci]
    steps: [{{run: echo ok}}]
  group:
    runs-on: {{group: lab}}
    steps: [{{run: echo ok}}]
  variable:
    runs-on: >-
      ${{{{
        github.event_name != 'pull_request'
        && fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || '["ubuntu-latest"]')
        || fromJSON(vars.OMNI_PUBLIC_PR_RUNS_ON_JSON || '["ubuntu-latest"]')
      }}}}
    steps: [{{run: echo ok}}]
  matrix:
    strategy: {{matrix: {{os: [ubuntu-latest]}}}}
    runs-on: ${{{{ matrix.os }}}}
    steps: [{{run: echo ok}}]
  call:
    uses: OmniNode-ai/omnibase_core/.github/workflows/x.yml@abc
"""
FIXTURE_SELF_HOSTED = ("group", "labels", "literal", "matrix", "variable")


def _workflow(**jobs: str) -> str:
    body = "".join(
        f"  {name}:\n    runs-on: {runs_on}\n    steps:\n      - run: echo ok\n"
        for name, runs_on in jobs.items()
    )
    return f"name: ci\non: [pull_request]\njobs:\n{body}"


def _run(head: dict[str, str], *, public: bool = True) -> ModelValidationReport:
    return HandlerPublicRunnerPlacement().handle(
        ModelPublicRunnerPlacementInput(
            repository="omnibase_infra",
            public=public,
            files=tuple(ModelSourceFile(path=p, source=s) for p, s in head.items()),
        )
    )


@pytest.mark.parametrize(
    ("runs_on", "kind"),
    [
        ("ubuntu-latest", None),
        ("ubuntu-22.04", None),
        ("windows-latest", None),
        ("macos-14", None),
        (["ubuntu-latest"], None),
        ("self-hosted", "self_hosted_label"),
        ("omnibase-ci", "self_hosted_label"),
        (["self-hosted", "omnibase-ci"], "self_hosted_label"),
        (["ubuntu-latest", "gpu"], "self_hosted_label"),
        ({"group": "lab"}, "self_hosted_label"),
        ({"labels": ["self-hosted"]}, "self_hosted_label"),
        ({"labels": ["ubuntu-latest"]}, None),
        ("${{ 'ubuntu-latest' }}", None),
        (
            "${{ github.event_name == 'push' && 'ubuntu-latest' || 'ubuntu-22.04' }}",
            None,
        ),
        ("${{ fromJSON('[\"ubuntu-latest\"]') }}", None),
        ('${{ fromJSON(\'["ubuntu-latest", "macos-14"]\') }}', None),
        ('${{ fromJSON(\'["ubuntu-latest", "omnibase-ci"]\') }}', "computed"),
        ("${{ fromJSON('[\"\"]') }}", "computed"),
        (COMPUTED, "computed"),
        ("${{ fromJSON(vars.LAB_PROBE_RUNS_ON_JSON) }}", "computed"),
        ("${{ fromJSON(needs.route.outputs.labels) }}", "computed"),
        ("${{ matrix.os }}", "computed"),
        (
            "${{ github.event_name == 'push' && 'my-box' || 'ubuntu-latest' }}",
            "computed",
        ),
        (None, None),
    ],
)
def test_runs_on_kind(runs_on: object, kind: str | None) -> None:
    assert runs_on_kind(runs_on) == kind


@pytest.mark.parametrize(
    ("runs_on", "kind"),
    [
        # A public repository can never take the parenthesized branch.
        (PRIVATE_GUARDED, None),
        (
            "${{ github.event.repository.private && (fromJSON(vars.X)) "
            "|| fromJSON('[\"ubuntu-latest\"]') }}",
            None,
        ),
        (
            "${{\n  github.event.repository.private && (\n    (a && b)\n    "
            "|| fromJSON(vars.X || '[\")\"]')\n  ) || 'ubuntu-latest'\n}}",
            None,
        ),
        # Without parentheses an inner `||` would bind outside the guard.
        (
            "${{ github.event.repository.private && vars.A || vars.B "
            "|| 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) || (vars.B) "
            "|| 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) && (vars.B) "
            "|| 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) || 'omnibase-ci' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) || vars.B }}",
            "computed",
        ),
        (
            "${{ !github.event.repository.private && (vars.A) || 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A || 'ubuntu-latest' }}",
            "computed",
        ),
    ],
)
def test_private_caller_guard_is_proved_hosted_only_in_its_exact_shape(
    runs_on: str, kind: str | None
) -> None:
    assert runs_on_kind(runs_on) == kind


@pytest.mark.timeout(2)
@pytest.mark.parametrize(("ending", "kind"), [("", None), ("]", "computed")])
def test_runs_on_json_array_repeated_empty_labels(
    ending: str, kind: str | None
) -> None:
    array = '[""' + ' ""' * 10_000 + ending
    expression = "${{ fromJSON('" + array + "') }}"
    assert runs_on_kind(expression) == kind


def test_reusable_workflow_call_has_no_runs_on() -> None:
    source = "on: [pull_request]\njobs:\n  call:\n    uses: OmniNode-ai/omnibase_core/.github/workflows/x.yml@abc\n"
    assert self_hosted_jobs(source, CI) == {}


def test_hosted_only_public_repository_passes_clean() -> None:
    report = _run({CI: _workflow(lint=HOSTED, test="windows-latest")})
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_fixture_public_workflow_refuses_every_self_hosted_job() -> None:
    """AC1 (OMN-21280): every job that is or may resolve to self-hosted FAILs."""
    report = _run({CI: FIXTURE_PUBLIC_WORKFLOW})
    assert report.overall_status == "FAIL"
    assert all(f.severity == "FAIL" for f in report.findings)
    assert sorted(f.location for f in report.findings) == [
        f"{CI}:jobs.{job}" for job in FIXTURE_SELF_HOSTED
    ]
    assert all("self_hosted_in_public" in f.message for f in report.findings)


def test_the_check_has_no_baseline_to_excuse_a_job() -> None:
    """AC1 (OMN-21280): the input carries no baseline, and one passed is refused."""
    assert set(ModelPublicRunnerPlacementInput.model_fields) == {
        "repository",
        "public",
        "files",
    }
    with pytest.raises(ValidationError):
        ModelPublicRunnerPlacementInput.model_validate(
            {"repository": "omnibase_infra", "baseline": [[CI, "literal"]]}
        )


def test_negative_control_self_hosted_job_fails() -> None:
    report = _run({CI: _workflow(lint=HOSTED, probe=LAB)})
    assert report.overall_status == "FAIL"
    [finding] = report.findings
    assert finding.location == f"{CI}:jobs.probe"


def test_negative_control_computed_job_fails() -> None:
    report = _run({CI: _workflow(probe=COMPUTED)})
    assert report.overall_status == "FAIL"


def test_the_same_jobs_in_a_private_repository_pass() -> None:
    report = _run({CI: FIXTURE_PUBLIC_WORKFLOW}, public=False)
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_invalid_workflow_is_an_error() -> None:
    report = _run({CI: "jobs: [unclosed"})
    assert report.overall_status == "ERROR"


# --- CLI over real git clones -------------------------------------------------


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(cwd),
        },
    ).stdout.strip()


def _repo(tmp_path: Path, workflow: str) -> Path:
    repo = tmp_path / "omnibase_infra"
    target = repo / CI
    target.parent.mkdir(parents=True)
    target.write_text(workflow)
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c")
    return repo


def test_cli_fails_a_public_repository_with_a_self_hosted_job(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path, FIXTURE_PUBLIC_WORKFLOW)
    assert cli.main(["--root", str(repo), "--repo", "omnibase_infra"]) == 1
    out = capsys.readouterr().out
    for job in FIXTURE_SELF_HOSTED:
        assert f"{CI}:jobs.{job}" in out


def test_cli_passes_a_hosted_public_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _workflow(lint=HOSTED, routed=PRIVATE_GUARDED))
    assert cli.main(["--root", str(repo), "--repo", "omnibase_infra"]) == 0


def test_cli_private_repository_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path, FIXTURE_PUBLIC_WORKFLOW)
    argv = ["--root", str(repo), "--visibility", "private"]
    assert cli.main(argv) == 0


@pytest.mark.parametrize(
    "flag", ["--baseline", "--base-ref", "--baseline-ratchet-base-ref"]
)
def test_cli_refuses_the_retired_baseline_flags(tmp_path: Path, flag: str) -> None:
    """OMN-21280: no flag brings a baseline or a base comparison back."""
    repo = _repo(tmp_path, _workflow(lint=HOSTED))
    with pytest.raises(SystemExit) as exc:
        cli.main(["--root", str(repo), flag, "x"])
    assert exc.value.code == 2


def test_omnibase_core_passes_its_own_check() -> None:
    """Positive control: core's own workflows, with no baseline (OMN-21280)."""
    root = Path(__file__).resolve().parents[3]
    assert cli.main(["--root", str(root), "--repo", "omnibase_core"]) == 0

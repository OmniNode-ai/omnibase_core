# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the public-repository runner placement check (OMN-19998).

RULING 2026-10-16T07:07:09Z: "Ci runners should be for private repos only."
The negative controls are the FAIL cases: a public repository that adds a
self-hosted job must fail, and the same job in a private repository must not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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


def _workflow(**jobs: str) -> str:
    body = "".join(
        f"  {name}:\n    runs-on: {runs_on}\n    steps:\n      - run: echo ok\n"
        for name, runs_on in jobs.items()
    )
    return f"name: ci\non: [pull_request]\njobs:\n{body}"


def _run(
    head: dict[str, str],
    *,
    base: dict[str, str] | None = None,
    baseline: frozenset[tuple[str, str]] = frozenset(),
    public: bool = True,
    stale: bool = False,
) -> ModelValidationReport:
    return HandlerPublicRunnerPlacement().handle(
        ModelPublicRunnerPlacementInput(
            repository="omnibase_infra",
            public=public,
            files=tuple(ModelSourceFile(path=p, source=s) for p, s in head.items()),
            base_files=(
                None
                if base is None
                else tuple(ModelSourceFile(path=p, source=s) for p, s in base.items())
            ),
            baseline=baseline,
            report_stale_baseline=stale,
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


def test_reusable_workflow_call_has_no_runs_on() -> None:
    source = "on: [pull_request]\njobs:\n  call:\n    uses: OmniNode-ai/omnibase_core/.github/workflows/x.yml@abc\n"
    assert self_hosted_jobs(source, CI) == {}


def test_hosted_only_public_repository_passes_clean() -> None:
    report = _run({CI: _workflow(lint=HOSTED, test="windows-latest")})
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_negative_control_added_self_hosted_job_fails() -> None:
    report = _run(
        {CI: _workflow(lint=HOSTED, probe=LAB)}, base={CI: _workflow(lint=HOSTED)}
    )
    assert report.overall_status == "FAIL"
    [finding] = [f for f in report.findings if f.severity == "FAIL"]
    assert finding.location == f"{CI}:jobs.probe"
    assert "not_in_baseline" in finding.message


def test_negative_control_added_computed_job_fails() -> None:
    report = _run({CI: _workflow(probe=COMPUTED)})
    assert report.overall_status == "FAIL"


def test_the_same_job_in_a_private_repository_passes() -> None:
    report = _run({CI: _workflow(probe=LAB)}, public=False)
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_baselined_job_warns_once_per_file() -> None:
    head = {CI: _workflow(a=LAB, b=COMPUTED, c=HOSTED)}
    report = _run(head, base=head, baseline=frozenset({(CI, "a"), (CI, "b")}))
    assert report.overall_status == "WARN"
    [finding] = report.findings
    assert finding.severity == "WARN"
    assert "2 baselined" in finding.message


def test_baselined_job_without_a_base_is_not_re_added() -> None:
    report = _run({CI: _workflow(a=LAB)}, baseline=frozenset({(CI, "a")}))
    assert report.overall_status == "WARN"


def test_baselined_job_the_base_did_not_run_self_hosted_fails() -> None:
    """A removed-then-re-added job, or one flipped to self-hosted, reuses a stale entry."""
    baseline = frozenset({(CI, "a")})
    absent = _run(
        {CI: _workflow(a=LAB)}, base={CI: _workflow(b=HOSTED)}, baseline=baseline
    )
    flipped = _run(
        {CI: _workflow(a=LAB)}, base={CI: _workflow(a=HOSTED)}, baseline=baseline
    )
    for report in (absent, flipped):
        assert report.overall_status == "FAIL"
        assert "re_added" in report.findings[0].message


def test_new_file_with_a_baselined_name_is_re_added() -> None:
    baseline = frozenset({(CI, "a")})
    report = _run({CI: _workflow(a=LAB)}, base={}, baseline=baseline)
    assert report.overall_status == "FAIL"


def test_unparsable_base_file_does_not_trigger_re_added() -> None:
    baseline = frozenset({(CI, "a")})
    report = _run(
        {CI: _workflow(a=LAB)}, base={CI: "jobs: [unclosed"}, baseline=baseline
    )
    assert report.overall_status == "WARN"


def test_removing_a_job_is_allowed_and_stale_baseline_warns() -> None:
    baseline = frozenset({(CI, "a"), (CI, "gone")})
    head = {CI: _workflow(a=LAB)}
    report = _run(head, base=head, baseline=baseline, stale=True)
    assert report.overall_status == "WARN"
    assert any("gone" in f.message and "remove" in f.message for f in report.findings)


def test_stale_entries_are_silent_unless_asked() -> None:
    report = _run({CI: _workflow(lint=HOSTED)}, baseline=frozenset({(CI, "gone")}))
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


def _commit(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "omnibase_infra"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _commit(repo, {CI: _workflow(lint=HOSTED)})
    _git(repo, "branch", "base")
    return repo


def _baseline(tmp_path: Path, jobs: str) -> Path:
    path = tmp_path / "baseline.yaml"
    path.write_text(f"repos:\n  omnibase_infra:\n    {CI}:\n{jobs}")
    return path


def test_cli_fails_a_pull_request_that_adds_a_self_hosted_job(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {CI: _workflow(lint=HOSTED, probe=LAB)})
    code = cli.main(
        ["--root", str(repo), "--repo", "omnibase_infra", "--base-ref", "base",
         "--baseline", str(_baseline(tmp_path, "      - other\n"))]
    )  # fmt: skip
    assert code == 1
    assert f"{CI}:jobs.probe" in capsys.readouterr().out


def test_cli_passes_when_the_job_is_baselined_and_unchanged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {CI: _workflow(probe=LAB)})
    _git(repo, "branch", "-f", "base")
    _commit(repo, {CI: _workflow(probe=LAB, lint=HOSTED)})
    baseline = _baseline(tmp_path, "      - probe\n")
    argv = ["--root", str(repo), "--repo", "omnibase_infra", "--base-ref", "base",
            "--baseline", str(baseline)]  # fmt: skip
    assert cli.main(argv) == 0


def test_cli_private_repository_passes_with_an_added_job(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {CI: _workflow(probe=LAB)})
    argv = ["--root", str(repo), "--repo", "omnibase_infra", "--visibility", "private",
            "--baseline", str(_baseline(tmp_path, "      - other\n"))]  # fmt: skip
    assert cli.main(argv) == 0


def test_cli_unknown_base_ref_is_an_error_never_a_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    argv = ["--root", str(repo), "--repo", "omnibase_infra", "--base-ref", "nope",
            "--baseline", str(_baseline(tmp_path, "      - other\n"))]  # fmt: skip
    assert cli.main(argv) == 1
    assert "not in the clone" in capsys.readouterr().out


def test_cli_baseline_may_shrink_but_not_grow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holder = tmp_path / "core"
    holder.mkdir()
    _git(holder, "init", "-q", "-b", "dev")
    name = "baseline.yaml"
    body = f"repos:\n  omnibase_infra:\n    {CI}:\n"
    _commit(holder, {name: body + "      - a\n      - b\n"})
    _git(holder, "branch", "base")
    repo = _repo(tmp_path)
    argv = ["--root", str(repo), "--repo", "omnibase_infra", "--baseline",
            str(holder / name), "--baseline-ratchet-base-ref", "base"]  # fmt: skip

    (holder / name).write_text(body + "      - a\n")
    assert cli.main(argv) == 0

    (holder / name).write_text(body + "      - a\n      - b\n      - c\n")
    assert cli.main(argv) == 1
    assert "baseline grew" in capsys.readouterr().out


def test_cli_baseline_ratchet_with_unknown_ref_is_an_error(tmp_path: Path) -> None:
    holder = tmp_path / "core"
    holder.mkdir()
    _git(holder, "init", "-q", "-b", "dev")
    _commit(holder, {"baseline.yaml": "repos: {}\n"})
    repo = _repo(tmp_path)
    argv = ["--root", str(repo), "--repo", "omnibase_infra", "--baseline",
            str(holder / "baseline.yaml"), "--baseline-ratchet-base-ref", "nope"]  # fmt: skip
    assert cli.main(argv) == 1


def test_shipped_baseline_names_the_public_repositories() -> None:
    baseline = cli.parse_baseline(cli.DEFAULT_BASELINE.read_text("utf-8"))
    assert set(baseline.repos) == {
        "omnibase_core",
        "omnibase_infra",
        "omniclaude",
        "omnimarket",
    }
    assert len(baseline.entries()) > 400


def test_omnibase_core_passes_its_own_check() -> None:
    """Positive control: core's own workflows against the shipped baseline."""
    root = Path(__file__).resolve().parents[3]
    assert cli.main(["--root", str(root), "--repo", "omnibase_core"]) == 0

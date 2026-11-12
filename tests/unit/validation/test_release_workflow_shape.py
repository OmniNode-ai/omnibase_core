# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shape + behaviour gate for ``.github/workflows/release.yml`` (OMN-15603).

omnibase-core 0.46.8 shipped as a **wheel-only** release: the single
non-idempotent ``Publish to PyPI`` step uploaded the 6.4 MiB wheel in 170-216s,
then died on the 9.2 MiB sdist at 241.4s -- identical to the tenth of a second
across two attempts of run 30674223657 -- with an HTTP 500 returned *after* the
full body had been transferred. That is upload.pypi.org's ~240s server-side
request deadline meeting the self-hosted runner's measured 30-39 KiB/s egress,
not a flake. Because every downstream step was sequenced behind that one step,
``Generate checksums`` / ``Set release tag`` / ``Create GitHub Release`` /
``Dependency Cascade`` all skipped, the run preserved zero artifacts, and no
re-run could make progress because the publish re-transferred the wheel it had
already landed.

The tests below are deliberately split into two kinds:

* **Shape** assertions, parsing the real workflow YAML (job graph, step order,
  runner, recovery inputs).
* **Behaviour** assertions, which extract a step's real ``run:`` script out of
  the real workflow file and *execute it* under ``bash -e`` (the shell GitHub
  Actions uses) against stubbed ``uv``/``sleep``/``curl`` on ``PATH``. Both
  shell steps -- ``Publish to PyPI`` and ``Report partial release state`` --
  are covered this way. Nothing is re-implemented here: a regression in the
  committed shell is a regression in these tests. Both steps therefore have to
  stay free of inline ``${{ }}`` expressions (values arrive through ``env:``),
  which the harnesses assert -- an expression would make the committed shell
  unrunnable here and quietly turn these tests into string matching.

``Report partial release state`` is a **job**, not a step inside ``release``:
a step inside ``release`` cannot observe the failure of ``release`` itself.

OMN-18594: the reusable Dependency Cascade is no longer called from this
workflow (downstream pins move only when the downstream needs something new;
run by workflow_dispatch), so the report watches ``release`` alone. It still
alarms on a failed or cancelled ``release``.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "release.yml"
)

# The simple-index ROOT, not the package page. uv appends the package name
# itself; see test_publish_uses_the_simple_index_root_not_the_package_page.
_EXPECTED_CHECK_URL = "--check-url https://pypi.org/simple/"

_PUBLISH_STEP = "Publish to PyPI"
_CHECKSUMS_STEP = "Generate checksums"
_TAG_STEP = "Set release tag"
_UPLOAD_STEP = "Upload dist artifacts"
_RELEASE_STEP = "Create GitHub Release"
_PARTIAL_STATE_STEP = "Report partial release state"

_RELEASE_JOB = "release"
_CASCADE_JOB = "dependency-cascade"
_PARTIAL_STATE_JOB = "report-partial-state"


# --------------------------------------------------------------------------
# workflow parsing helpers
# --------------------------------------------------------------------------
def _as_mapping(value: object, what: str) -> dict[object, object]:
    assert isinstance(value, dict), f"{what} must be a mapping, got {type(value)}"
    return value


def _workflow() -> dict[object, object]:
    return _as_mapping(yaml.safe_load(WORKFLOW_PATH.read_text()), "release.yml")


def _triggers() -> dict[object, object]:
    """YAML 1.1 parses a bare ``on:`` key as the boolean ``True``."""
    workflow = _workflow()
    key: object = True if True in workflow else "on"
    return _as_mapping(workflow[key], "release.yml `on:`")


def _jobs() -> dict[object, object]:
    return _as_mapping(_workflow()["jobs"], "release.yml `jobs:`")


def _job(name: str) -> dict[object, object]:
    jobs = _jobs()
    assert name in jobs, f"release.yml must define a `{name}` job; has {list(jobs)}"
    return _as_mapping(jobs[name], f"the `{name}` job")


def _release_job() -> dict[object, object]:
    return _job(_RELEASE_JOB)


def _job_steps(job: dict[object, object]) -> list[dict[object, object]]:
    steps = job["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _steps() -> list[dict[object, object]]:
    return _job_steps(_release_job())


def _step_index(name: str) -> int:
    for index, step in enumerate(_steps()):
        if step.get("name") == name:
            return index
    raise AssertionError(f"release job must have a step named {name!r}")


def _step(name: str) -> dict[object, object]:
    return _steps()[_step_index(name)]


def test_main_sync_app_token_can_write_tagged_workflows() -> None:
    """A release fast-forward may include changes beneath .github/workflows/."""
    mint_step = _step("Mint onexbot-occ-writer app token")
    token_scope = _as_mapping(mint_step["with"], "main-sync App token `with:`")
    assert token_scope["permission-workflows"] == "write"


def _partial_state_step() -> dict[object, object]:
    """The partial-state report lives in its own job, not in ``release``.

    A step inside ``release`` cannot observe a failure of ``release`` itself,
    which AC4 names explicitly; see
    ``test_partial_release_state_job_alarms_on_a_failed_or_cancelled_release``.
    """
    for step in _job_steps(_job(_PARTIAL_STATE_JOB)):
        if step.get("name") == _PARTIAL_STATE_STEP:
            return step
    raise AssertionError(
        f"the `{_PARTIAL_STATE_JOB}` job must have a step named {_PARTIAL_STATE_STEP!r}"
    )


def _publish_script() -> str:
    run = _step(_PUBLISH_STEP)["run"]
    assert isinstance(run, str)
    return run


# --------------------------------------------------------------------------
# behaviour harness: run the REAL publish script with a stubbed uv + sleep
# --------------------------------------------------------------------------
_STUB_UV = """#!/bin/bash
printf '%s\\n' "$*" >> "$UV_STUB_ARGV_LOG"
printf 'x' >> "$UV_STUB_COUNTER"
attempts=$(($(wc -c < "$UV_STUB_COUNTER")))
if [ "$attempts" -le "$UV_STUB_FAIL_TIMES" ]; then
  echo "$UV_STUB_FAIL_MESSAGE" >&2
  exit 1
fi
echo "Uploaded ok"
exit 0
"""

# What upload.pypi.org actually emits when a request overruns its ~240s
# server-side deadline -- the exact 0.46.8 failure.
_UV_5XX_MESSAGE = (
    "Failed to publish `dist/omnibase_core-0.46.8.tar.gz` to "
    "https://upload.pypi.org/legacy/\n"
    "  Caused by: Upload failed with status code 500 Internal Server Error."
)
# A deterministic, permanent rejection. Retrying this cannot help.
_UV_4XX_MESSAGE = (
    "Failed to publish `dist/omnibase_core-0.46.8.tar.gz` to "
    "https://upload.pypi.org/legacy/\n"
    "  Caused by: Upload failed with status code 403 Forbidden. "
    "Invalid or non-existent authentication information."
)

_STUB_SLEEP = """#!/bin/bash
printf '%s\\n' "$1" >> "$SLEEP_STUB_LOG"
exit 0
"""


@dataclass(frozen=True)
class _PublishRun:
    returncode: int
    stdout: str
    stderr: str
    uv_invocations: list[str]
    sleep_seconds: list[int]


def _run_publish_script(
    tmp_path: Path,
    *,
    fail_times: int,
    fail_message: str = _UV_5XX_MESSAGE,
) -> _PublishRun:
    """Execute the committed publish shell with ``uv``/``sleep`` stubbed out."""
    script = _publish_script()
    # A GH expression would make the committed shell unexecutable here and the
    # harness silently vacuous, so the step must stay expression-free.
    assert "${{" not in script, (
        "the publish step must contain no ${{ }} expressions so that its real "
        "shell can be executed under test"
    )

    script_path = tmp_path / "publish_step.sh"
    script_path.write_text(script)

    workdir = tmp_path / "work"
    (workdir / "dist").mkdir(parents=True)
    (workdir / "dist" / "omnibase_core-9.9.9-py3-none-any.whl").write_text("wheel")
    (workdir / "dist" / "omnibase_core-9.9.9.tar.gz").write_text("sdist")

    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    for name, body in (("uv", _STUB_UV), ("sleep", _STUB_SLEEP)):
        stub = stub_bin / name
        stub.write_text(body)
        stub.chmod(0o755)

    argv_log = tmp_path / "uv_argv.log"
    counter = tmp_path / "uv_counter"
    sleep_log = tmp_path / "sleep.log"
    for artifact in (argv_log, counter, sleep_log):
        artifact.write_text("")

    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{stub_bin}{os.pathsep}{env['PATH']}",
            "UV_STUB_ARGV_LOG": str(argv_log),
            "UV_STUB_COUNTER": str(counter),
            "UV_STUB_FAIL_TIMES": str(fail_times),
            "UV_STUB_FAIL_MESSAGE": fail_message,
            "SLEEP_STUB_LOG": str(sleep_log),
            "UV_PUBLISH_TOKEN": "pypi-test-token",
        }
    )

    # `bash -e <file>` is exactly the shell GitHub Actions runs `run:` under.
    proc = subprocess.run(
        ["bash", "-e", str(script_path)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return _PublishRun(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        uv_invocations=[
            line for line in argv_log.read_text().splitlines() if line.strip()
        ],
        sleep_seconds=[
            int(line) for line in sleep_log.read_text().splitlines() if line.strip()
        ],
    )


# --------------------------------------------------------------------------
# behaviour harness: run the REAL partial-state script with a stubbed curl
# --------------------------------------------------------------------------
_STUB_CURL = """#!/bin/bash
printf '%s\\n' "$*" >> "$CURL_STUB_ARGV_LOG"
if [ "$CURL_STUB_FAIL" = "1" ]; then
  exit 6
fi
cat "$CURL_STUB_BODY"
exit 0
"""


@dataclass(frozen=True)
class _PartialStateRun:
    returncode: int
    stdout: str
    stderr: str
    curl_invocations: list[str]


def _run_partial_state_script(
    tmp_path: Path,
    *,
    release_tag: str,
    dist_files: tuple[str, ...],
    index_files: tuple[str, ...] = (),
    curl_fails: bool = False,
    release_result: str = "failure",
    bind_env: bool = True,
) -> _PartialStateRun:
    """Execute the committed partial-state shell with ``curl`` stubbed out.

    This block is the one thing a stranded release has left to tell a human
    what happened, and it only ever runs on the failure path -- so it is
    exactly the shell most likely to ship a latent ``set -u`` / glob / errexit
    bug unnoticed. Asserting on the ``run:`` string cannot catch that; running
    it can.

    ``bind_env=False`` removes ``RELEASE_TAG`` / ``RELEASE_RESULT`` from the
    child environment entirely, which is what makes
    the ``${VAR:-}`` guards in the committed shell load-bearing rather than
    decorative -- see
    ``test_partial_release_state_survives_an_entirely_unbound_environment``.
    """
    step = _partial_state_step()
    script = str(step["run"])
    # The tag must arrive via `env:`, not an inline expression -- otherwise the
    # committed shell is unexecutable here and this harness goes vacuous.
    assert "${{" not in script, (
        "the partial-state step must contain no ${{ }} expressions so that its "
        "real shell can be executed under test"
    )
    step_env = _as_mapping(step["env"], f"{_PARTIAL_STATE_STEP} `env:`")
    # The report is a separate job now, so the tag arrives off the `release`
    # job's declared output, not off a sibling step in the same job.
    assert step_env["RELEASE_TAG"] == "${{ needs.release.outputs.version }}"
    assert step_env["RELEASE_RESULT"] == "${{ needs.release.result }}"
    assert "CASCADE_RESULT" not in step_env, step_env

    script_path = tmp_path / "partial_state_step.sh"
    script_path.write_text(script)

    workdir = tmp_path / "work"
    (workdir / "dist").mkdir(parents=True)
    for name in dist_files:
        (workdir / "dist" / name).write_text("artifact")

    body = tmp_path / "index.html"
    body.write_text(
        "<html><body>"
        + "".join(f'<a href="/x/{name}">{name}</a>' for name in index_files)
        + "</body></html>"
    )

    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    stub = stub_bin / "curl"
    stub.write_text(_STUB_CURL)
    stub.chmod(0o755)

    argv_log = tmp_path / "curl_argv.log"
    argv_log.write_text("")

    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{stub_bin}{os.pathsep}{env['PATH']}",
            "CURL_STUB_ARGV_LOG": str(argv_log),
            "CURL_STUB_BODY": str(body),
            "CURL_STUB_FAIL": "1" if curl_fails else "0",
        }
    )
    if bind_env:
        env.update(
            {
                "RELEASE_TAG": release_tag,
                "RELEASE_RESULT": release_result,
            }
        )
    else:
        for unbound in ("RELEASE_TAG", "RELEASE_RESULT"):
            env.pop(unbound, None)

    proc = subprocess.run(
        ["bash", "-e", str(script_path)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return _PartialStateRun(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        curl_invocations=[
            line for line in argv_log.read_text().splitlines() if line.strip()
        ],
    )


# --------------------------------------------------------------------------
# AC1 -- resumable publish
# --------------------------------------------------------------------------
def test_publish_passes_check_url_so_already_landed_files_are_skipped(
    tmp_path: Path,
) -> None:
    """AC1: every real uv invocation carries --check-url."""
    run = _run_publish_script(tmp_path, fail_times=0)

    assert run.returncode == 0, run.stderr
    assert run.uv_invocations, "publish step never invoked uv"
    for invocation in run.uv_invocations:
        assert invocation.startswith("publish "), invocation
        assert _EXPECTED_CHECK_URL in invocation, invocation


def test_publish_uses_the_simple_index_root_not_the_package_page(
    tmp_path: Path,
) -> None:
    """AC1, exists-but-wrong guard.

    OMN-15603 names ``--check-url https://pypi.org/simple/omnibase-core/`` as a
    candidate. Measured against uv 0.12.1 -- the version
    ``astral-sh/setup-uv@v7`` resolves -- with the already-published 0.46.8
    wheel:

    * ``--check-url https://pypi.org/simple/`` ->
      ``File omnibase_core-0.46.8-py3-none-any.whl already exists, skipping``
    * ``--check-url https://pypi.org/simple/omnibase-core/`` -> ``Uploading
      omnibase_core-0.46.8-py3-none-any.whl (6.4MiB)``, byte-identical to
      passing no ``--check-url`` at all.

    uv joins the package name onto the URL itself, so the package-scoped form
    resolves ``/simple/omnibase-core/omnibase-core/`` and silently degrades to
    a full re-upload. A "present but wrong" --check-url is exactly the failure
    this test exists to catch -- AC1 is unmet without this assertion.
    """
    run = _run_publish_script(tmp_path, fail_times=0)

    for invocation in run.uv_invocations:
        assert "https://pypi.org/simple/omnibase-core" not in invocation, (
            "package-scoped --check-url does not skip existing files on uv "
            f"0.12.1; use the simple index root: {invocation}"
        )


# --------------------------------------------------------------------------
# AC3 -- retry with backoff, fail-closed
# --------------------------------------------------------------------------
def test_publish_retries_at_least_twice_with_increasing_backoff(
    tmp_path: Path,
) -> None:
    """AC3: >= 2 retries (3 attempts total) with a growing backoff."""
    run = _run_publish_script(tmp_path, fail_times=99)

    assert len(run.uv_invocations) >= 3, run.uv_invocations
    assert len(run.sleep_seconds) >= 2, run.sleep_seconds
    assert all(seconds > 0 for seconds in run.sleep_seconds), run.sleep_seconds
    assert run.sleep_seconds == sorted(run.sleep_seconds), run.sleep_seconds
    assert run.sleep_seconds[-1] > run.sleep_seconds[0], run.sleep_seconds


def test_publish_fails_closed_when_every_attempt_fails(tmp_path: Path) -> None:
    """Negative case: exhausted retries must fail the job, not swallow the 5xx."""
    run = _run_publish_script(tmp_path, fail_times=99)

    assert run.returncode != 0, (
        "publish must propagate failure after exhausting retries; "
        f"stdout={run.stdout!r} stderr={run.stderr!r}"
    )
    assert "failed after" in run.stderr, run.stderr

    script = _publish_script()
    assert "|| true" not in script, script
    assert "continue-on-error" not in str(_step(_PUBLISH_STEP)), _step(_PUBLISH_STEP)


def test_publish_recovers_when_a_transient_5xx_clears(tmp_path: Path) -> None:
    """AC3: a retry that succeeds must succeed the step, not just log."""
    run = _run_publish_script(tmp_path, fail_times=1)

    assert run.returncode == 0, run.stderr
    assert len(run.uv_invocations) == 2, run.uv_invocations
    assert len(run.sleep_seconds) == 1, run.sleep_seconds


def test_publish_stops_retrying_once_it_succeeds(tmp_path: Path) -> None:
    """Negative case: no unconditional retry loop -- one clean attempt is one."""
    run = _run_publish_script(tmp_path, fail_times=0)

    assert len(run.uv_invocations) == 1, run.uv_invocations
    assert run.sleep_seconds == [], run.sleep_seconds


def test_publish_does_not_retry_a_non_retryable_failure(tmp_path: Path) -> None:
    """AC3, exists-but-wrong guard: the retry must be *on 5xx*, not on any exit.

    ``until uv publish; do ...; done`` retries every non-zero exit, so a
    permanent 403 (bad token) or 400 (malformed metadata) burns the whole
    15s + 45s backoff and is then reported with ``retrying`` -- the language of
    a transient fault -- before failing anyway. AC3 as written says "on 5xx",
    so the loop has to read the failure. A retry loop that cannot tell a 500
    from a 403 satisfies the letter of "retries" and none of its intent.
    """
    run = _run_publish_script(tmp_path, fail_times=99, fail_message=_UV_4XX_MESSAGE)

    assert run.returncode != 0, run.stdout
    assert len(run.uv_invocations) == 1, (
        "a 403 is deterministic; a second attempt cannot clear it: "
        f"{run.uv_invocations}"
    )
    assert run.sleep_seconds == [], (
        f"no backoff may be burned on a non-retryable failure: {run.sleep_seconds}"
    )
    assert "non-retryable" in run.stderr, run.stderr
    assert "retrying in" not in run.stderr, (
        "a permanent failure must not be reported in the language of a "
        f"transient one: {run.stderr}"
    )


def test_publish_still_retries_the_real_pypi_deadline_5xx(tmp_path: Path) -> None:
    """AC3 companion to the guard above: the 0.46.8 failure IS retryable.

    Uses the verbatim shape uv emits when upload.pypi.org returns 500 after the
    ~240s server-side deadline. A classifier tightened to the point where the
    actual observed failure stops being retried would pass the negative test
    above and silently un-fix the ticket.
    """
    run = _run_publish_script(tmp_path, fail_times=1, fail_message=_UV_5XX_MESSAGE)

    assert run.returncode == 0, run.stderr
    assert len(run.uv_invocations) == 2, run.uv_invocations
    assert run.sleep_seconds == [15], run.sleep_seconds


# --------------------------------------------------------------------------
# AC2 -- runner egress
# --------------------------------------------------------------------------
def test_release_job_runs_on_a_hosted_runner_with_pypi_egress() -> None:
    """AC2: the self-hosted runner cannot clear PyPI's ~240s deadline."""
    runs_on = str(_release_job()["runs-on"])

    assert "self-hosted" not in runs_on, runs_on
    assert "omnibase-ci" not in runs_on, runs_on
    assert "ubuntu" in runs_on, runs_on


# --------------------------------------------------------------------------
# AC4 -- post-publish work is not silently lost
# --------------------------------------------------------------------------
def test_checksums_and_release_tag_are_computed_before_publish() -> None:
    """AC4: pure local steps must not sit behind the non-idempotent publish."""
    publish = _step_index(_PUBLISH_STEP)

    assert _step_index(_CHECKSUMS_STEP) < publish
    assert _step_index(_TAG_STEP) < publish


def test_dist_artifacts_are_preserved_before_publish() -> None:
    """AC4: run 30674223657 kept zero artifacts, so recovery meant a rebuild."""
    upload = _step(_UPLOAD_STEP)

    assert _step_index(_UPLOAD_STEP) < _step_index(_PUBLISH_STEP)
    assert "actions/upload-artifact@" in str(upload["uses"])
    with_ = _as_mapping(upload["with"], f"{_UPLOAD_STEP} `with:`")
    assert with_["path"] == "dist/"
    assert with_["if-no-files-found"] == "error"


def test_partial_release_state_job_alarms_on_a_failed_or_cancelled_release() -> None:
    """AC4 (shape): the report still fires on a failed or cancelled ``release``.

    OMN-18594 removed the ``dependency-cascade`` job; the alarm for ``release``
    must not be weakened by that removal.
    """
    job = _job(_PARTIAL_STATE_JOB)

    assert job["needs"] == [_RELEASE_JOB], job["needs"]

    condition = str(job["if"])
    assert "always()" in condition, condition
    for upstream in (
        "needs.release.result == 'failure'",
        "needs.release.result == 'cancelled'",
    ):
        assert upstream in condition, f"{upstream!r} missing from {condition!r}"
    assert "dependency-cascade" not in condition, condition


def test_partial_release_state_does_not_fire_on_a_skipped_release() -> None:
    """AC4 (shape, negative): a skipped ``release`` is not a partial release.

    A sync-only dispatch skips ``release`` by design. A condition written as
    ``result != 'success'`` -- the obvious way to write this -- would report
    that as INCOMPLETE every time.
    """
    condition = str(_job(_PARTIAL_STATE_JOB)["if"])

    assert "!= 'success'" not in condition, condition
    assert "'skipped'" not in condition, condition


def test_dependency_cascade_is_not_called_from_the_release_workflow() -> None:
    """OMN-18594: downstream pins move only when the downstream needs something
    new; the release no longer opens pin-bump PRs."""
    assert _CASCADE_JOB not in _jobs(), list(_jobs())
    text = WORKFLOW_PATH.read_text()
    assert "dependency-cascade.yml" not in text
    assert "needs['dependency-cascade']" not in text


def test_partial_release_state_is_not_a_step_in_the_release_job() -> None:
    """AC4 (shape, net-negative-surface): exactly one copy of this shell.

    Keeping the old in-job step alongside the new job would leave two
    independently-drifting copies of the only diagnostic a stranded release
    emits.
    """
    release_step_names = [step.get("name") for step in _steps()]

    assert _PARTIAL_STATE_STEP not in release_step_names, release_step_names
    # ...and the release job still does the thing the report reports about.
    assert _RELEASE_STEP in release_step_names, release_step_names


def test_partial_release_state_names_landed_and_missing_artifacts(
    tmp_path: Path,
) -> None:
    """AC4 (behaviour): the exact 0.46.8 wreckage, executed, not pattern-matched.

    Wheel on the index, sdist not, tag resolved -- the report must say which is
    which and hand back a runnable recovery command.
    """
    run = _run_partial_state_script(
        tmp_path,
        release_tag="v0.46.8",
        dist_files=(
            "omnibase_core-0.46.8-py3-none-any.whl",
            "omnibase_core-0.46.8.tar.gz",
        ),
        index_files=("omnibase_core-0.46.8-py3-none-any.whl",),
    )

    assert run.returncode == 0, run.stderr
    assert "::error::RELEASE INCOMPLETE for v0.46.8" in run.stdout
    assert (
        "::error::LANDED on PyPI: omnibase_core-0.46.8-py3-none-any.whl" in run.stdout
    )
    assert "::error::MISSING from PyPI: omnibase_core-0.46.8.tar.gz" in run.stdout
    assert "dist-v0.46.8" in run.stdout
    assert "gh workflow run release.yml" in run.stdout
    assert "-f tag=v0.46.8" in run.stdout
    # It must actually consult the real public index, not a placeholder.
    assert any(
        "https://pypi.org/simple/omnibase-core/" in call
        for call in run.curl_invocations
    ), run.curl_invocations


def test_partial_release_state_survives_an_unresolved_tag_and_empty_dist(
    tmp_path: Path,
) -> None:
    """AC4 (behaviour, negative): failing before `Set release tag` is the case
    most likely to trip `set -u` -- the report must still emit, not crash."""
    run = _run_partial_state_script(tmp_path, release_tag="", dist_files=())

    assert run.returncode == 0, run.stderr
    assert "::error::RELEASE INCOMPLETE for <tag unresolved>" in run.stdout
    assert "No dist artifact can be claimed" in run.stdout
    assert "-f tag=<tag>" in run.stdout
    assert "LANDED on PyPI" not in run.stdout
    assert "MISSING from PyPI" not in run.stdout


def test_partial_release_state_reports_unknown_when_the_index_is_unreachable(
    tmp_path: Path,
) -> None:
    """AC4 (behaviour, negative): an unreadable index must not be reported as
    proof of absence -- claiming MISSING there is a false statement about a
    public index, and the recovery decision differs."""
    run = _run_partial_state_script(
        tmp_path,
        release_tag="v0.46.8",
        dist_files=(
            "omnibase_core-0.46.8-py3-none-any.whl",
            "omnibase_core-0.46.8.tar.gz",
        ),
        index_files=("omnibase_core-0.46.8-py3-none-any.whl",),
        curl_fails=True,
    )

    assert run.returncode == 0, run.stderr
    assert "landed/missing state is UNKNOWN" in run.stdout
    assert (
        "::error::UNKNOWN on PyPI: omnibase_core-0.46.8-py3-none-any.whl" in run.stdout
    )
    assert "::error::UNKNOWN on PyPI: omnibase_core-0.46.8.tar.gz" in run.stdout
    assert "LANDED on PyPI" not in run.stdout
    assert "MISSING from PyPI" not in run.stdout


def test_partial_release_state_names_a_failed_release_not_a_cascade(
    tmp_path: Path,
) -> None:
    """AC4 (behaviour): the report speaks only about ``release`` now."""
    run = _run_partial_state_script(
        tmp_path,
        release_tag="v0.46.8",
        dist_files=("omnibase_core-0.46.8-py3-none-any.whl",),
        index_files=("omnibase_core-0.46.8-py3-none-any.whl",),
        release_result="failure",
    )

    assert run.returncode == 0, run.stderr
    assert "::error::RELEASE INCOMPLETE for v0.46.8" in run.stdout
    assert "release job: failure" in run.stdout
    assert "GitHub Release did NOT run." in run.stdout
    assert "ascade" not in run.stdout


def test_partial_release_state_survives_an_entirely_unbound_environment(
    tmp_path: Path,
) -> None:
    """AC4 (behaviour, negative): the ``${VAR:-}`` guards must be load-bearing.

    Every other case in this file binds all three variables through the child
    env, exactly as Actions does via the step's ``env:`` block -- which means
    none of them would notice if the guards were deleted. This one removes the
    variables outright. Under ``set -u`` an unguarded expansion aborts the
    script, and the *only* diagnostic a stranded release emits disappears at
    the moment it is needed.
    """
    run = _run_partial_state_script(
        tmp_path,
        release_tag="",
        dist_files=("omnibase_core-0.46.8-py3-none-any.whl",),
        index_files=(),
        bind_env=False,
    )

    assert run.returncode == 0, (
        f"the report must not abort on an unbound variable: {run.stderr!r}"
    )
    assert "::error::RELEASE INCOMPLETE for <tag unresolved>" in run.stdout
    assert "release job: unknown" in run.stdout
    # The census still has to run: dist/ is readable regardless of the env.
    assert "::error::MISSING from PyPI: omnibase_core-0.46.8-py3-none-any.whl" in (
        run.stdout
    )
    assert "unbound variable" not in run.stderr, run.stderr


def test_release_job_outputs_survive_the_cascade_removal() -> None:
    """OMN-18594 regression guard: dropping the cascade caller keeps the
    ``release`` job's declared outputs, which the report and the release
    evidence step still read."""
    assert _release_job()["outputs"] == {
        "version": "${{ steps.tag.outputs.tag }}",
        "ticket": "${{ steps.release_evidence.outputs.ticket }}",
        "evidence_source": "${{ steps.release_evidence.outputs.evidence_source }}",
    }


def test_release_evidence_only_accepts_a_merged_pr() -> None:
    """CodeRabbit finding (OMN-16286): ``/commits/{sha}/pulls`` returns every
    PR associated with a commit, not just the merged one -- GitHub includes
    open PRs too when the commit is not yet on the default branch, and the
    endpoint documents no ordering guarantee. Selecting a bare ``.[0]`` risks
    propagating Evidence-Ticket/Evidence-Source from an open, unreviewed PR
    instead of the merged release PR that actually proved the code. The
    resolution step must filter to a genuinely merged PR (both at the list
    stage and via an explicit state re-check) and fail loud otherwise.
    """
    script = _step("Resolve release ticket + evidence (OMN-16286)")["run"]
    assert isinstance(script, str)

    # List-stage filter: closed AND merged_at set, not a bare .[0].
    assert 'select(.state == "closed" and .merged_at != null)' in script, script
    assert "][0].number" in script or "[0].number" in script, script
    assert ".[0].number // empty" not in script, (
        "must not select the first associated PR unconditionally -- that "
        f"can be an open, unmerged PR: {script}"
    )

    # Explicit re-check: even a closed+merged_at-filtered PR is re-verified
    # via a live `gh pr view --json state` before its body is trusted.
    assert "--json state --jq" in script, script
    assert 'pr_state" != "MERGED"' in script, script
    assert script.count("exit 1") >= 2, (
        "both the no-PR-found and the not-actually-merged paths must fail "
        f"loud: {script}"
    )


# --------------------------------------------------------------------------
# AC5 -- the recovery path a stranded version is repaired through
# --------------------------------------------------------------------------
def test_workflow_dispatch_recovery_checks_out_the_requested_tag() -> None:
    """AC5: a tag-triggered run uses the workflow AT THE TAG, so the repair for
    an already-cut version has to come through workflow_dispatch on a branch
    that carries the fix, checking out the stranded tag's tree."""
    triggers = _triggers()

    dispatch = _as_mapping(triggers["workflow_dispatch"], "`workflow_dispatch:`")
    inputs = _as_mapping(dispatch["inputs"], "`workflow_dispatch.inputs:`")
    tag_input = _as_mapping(inputs["tag"], "the `tag` dispatch input")
    # OMN-16289: `tag` stopped being a REQUIRED input when the sync-only
    # `sync_main_to_tag` dispatch landed -- a dispatch that only fast-forwards
    # main has no release tag to give. AC5's real invariant is that a release
    # dispatch cannot proceed WITHOUT one, which is now enforced by an explicit
    # guard step rather than by the form field.
    assert tag_input.get("required") is not True
    guard = _step("Require a release tag on workflow_dispatch")
    assert "sync_main_to_tag" in str(guard["run"])
    assert "exit 1" in str(guard["run"])

    checkout = _steps()[0]
    assert "actions/checkout@" in str(checkout["uses"])
    ref = str(_as_mapping(checkout["with"], "checkout `with:`")["ref"])
    assert "workflow_dispatch" in ref
    assert "inputs.tag" in ref


# --------------------------------------------------------------------------
# OMN-14355 -- a release PR without an Evidence-Source line must still release
# --------------------------------------------------------------------------
_RESOLVE_EVIDENCE_STEP = "Resolve release ticket + evidence (OMN-16286)"


def _run_resolve_evidence_script(
    tmp_path: Path, *, pr_body: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    """Execute the real ``Resolve release ticket + evidence`` step under bash.

    ``gh`` and ``git`` are stubbed on PATH; the two ``${{ }}`` expressions the
    step carries (``github.repository``) are substituted with a literal, since
    Actions would have expanded them before bash saw the script.
    """
    script = _step(_RESOLVE_EVIDENCE_STEP)["run"]
    assert isinstance(script, str)
    script = script.replace("${{ github.repository }}", "OmniNode-ai/omnibase_core")
    assert "${{" not in script, script

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    body_file = tmp_path / "pr_body.txt"
    body_file.write_text(pr_body)
    (bin_dir / "git").write_text("#!/bin/sh\necho " + "d" * 40 + "\n")
    (bin_dir / "gh").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        "  api*) echo 1965 ;;\n"
        '  *"--json state"*) echo MERGED ;;\n'
        f'  *"--json body"*) cat "{body_file}" ;;\n'
        "esac\n"
    )
    for tool in ("git", "gh"):
        (bin_dir / tool).chmod(0o755)

    github_output = tmp_path / "github_output"
    github_output.write_text("")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(github_output),
        "GH_TOKEN": "stub",
    }
    run = subprocess.run(
        ["bash", "-e", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    outputs = dict(
        line.split("=", 1) for line in github_output.read_text().splitlines() if line
    )
    return run, outputs


def test_release_evidence_resolves_with_a_ticket_and_no_evidence_source(
    tmp_path: Path,
) -> None:
    """OMN-14355: v0.47.43 was tagged but never published.

    Run 38485202286 died in this step with ``ticket='OMN-18595',
    evidence_source='<none>'``: since the change-control companion mint was
    retired (OMN-20074) a release PR body carries ``Evidence-Ticket:`` and no
    ``Evidence-Source:`` line, and the step demanded both. The cascade
    generator never writes the source into a bump PR (OMN-18202), so only the
    ticket is load-bearing; its absence must not stop the publish.
    """
    run, outputs = _run_resolve_evidence_script(
        tmp_path, pr_body="## Summary\n\nEvidence-Ticket: OMN-18595\n"
    )

    assert run.returncode == 0, run.stdout + run.stderr
    assert outputs["ticket"] == "OMN-18595"
    assert outputs["evidence_source"] == ""


def test_release_evidence_still_threads_an_evidence_source_when_present(
    tmp_path: Path,
) -> None:
    run, outputs = _run_resolve_evidence_script(
        tmp_path,
        pr_body="Evidence-Ticket: OMN-18595\nEvidence-Source: OCC#9159\n",
    )

    assert run.returncode == 0, run.stdout + run.stderr
    assert outputs["ticket"] == "OMN-18595"
    assert outputs["evidence_source"] == "OCC#9159"


def test_release_evidence_still_requires_a_ticket(tmp_path: Path) -> None:
    run, _ = _run_resolve_evidence_script(
        tmp_path, pr_body="Evidence-Source: OCC#9159\n"
    )

    assert run.returncode != 0
    assert "Evidence-Ticket" in run.stdout


# --------------------------------------------------------------------------
# OMN-23845 -- report-only release consistency, after a successful release
# --------------------------------------------------------------------------
# The report is the last step of the existing `release` job (a new job is
# refused by the CI-inheritance ratchet). The step runs only when every step
# before it succeeded, so only after a published release and a synced main, and
# it is `continue-on-error` and always exits 0: the pilot never fails a release.
_CONSISTENCY_STEP = "Report release consistency"
_MAIN_SYNC_STEP = "Sync main to release tag"
_CONSISTENCY_MODULE = (
    "omnibase_core.nodes.node_release_consistency_check_compute."
    "runtime_release_consistency_check"
)

# Recorded from the published omnibase-core 0.47.72 release (2026-11-12): its
# SHA256SUMS.txt asset, whose two sha256 values PyPI's JSON for 0.47.72 served.
_C_TAG = "v0.47.72"
_C_WHEEL = "omnibase_core-0.47.72-py3-none-any.whl"
_C_SDIST = "omnibase_core-0.47.72.tar.gz"
_C_SUMS = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "release_consistency"
    / "v0_47_72"
    / "SHA256SUMS.txt"
).read_text(encoding="utf-8")
_C_RECORDED = {
    Path(path).name: digest
    for digest, path in (line.split() for line in _C_SUMS.splitlines() if line)
}
_C_WHEEL_SHA = _C_RECORDED[_C_WHEEL]
_C_SDIST_SHA = _C_RECORDED[_C_SDIST]

# Writes the canned body to the file named by `-o`, so the committed shell's
# own `curl ... -o pypi.json` is what is exercised.
_STUB_CURL_TO_FILE = """#!/bin/bash
printf '%s\\n' "$*" >> "$CURL_STUB_ARGV_LOG"
if [ "$CURL_STUB_FAIL" = "1" ]; then
  exit 22
fi
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    out="$2"
    shift
  fi
  shift
done
cat "$CURL_STUB_BODY" > "$out"
exit 0
"""

# Stands in for `uv run ... --with <built wheel> python -m <module> ...`: logs
# its argv and runs the module after `python` with this test's interpreter,
# which has the checkout's omnibase_core importable.
_STUB_UV_RUN_MODULE = """#!{python}
import os
import sys

argv = sys.argv[1:]
with open(os.environ["UV_STUB_ARGV_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(argv) + "\\n")
index = argv.index("python")
os.execv({python!r}, [{python!r}, *argv[index + 1 :]])
"""


@dataclass(frozen=True)
class _ConsistencyRun:
    returncode: int
    stdout: str
    curl_invocations: list[str]
    uv_invocations: list[str]
    summary: str


def _run_consistency_script(
    tmp_path: Path, *, sdist_sha_on_pypi: str, curl_fails: bool = False
) -> _ConsistencyRun:
    """Execute the committed consistency shell with curl, sleep and uv stubbed."""
    import json
    import sys
    import zipfile

    step = _step(_CONSISTENCY_STEP)
    script = str(step["run"])
    assert "${{" not in script, (
        "the consistency step must contain no ${{ }} expressions so that its "
        "real shell can be executed under test"
    )
    step_env = _as_mapping(step["env"], f"{_CONSISTENCY_STEP} `env:`")
    assert step_env["RELEASE_TAG"] == "${{ steps.tag.outputs.tag }}"

    script_path = tmp_path / "consistency_step.sh"
    script_path.write_text(script)

    workdir = tmp_path / "work"
    dist = workdir / "dist"
    dist.mkdir(parents=True)
    with zipfile.ZipFile(dist / _C_WHEEL, "w") as wheel:
        wheel.writestr(
            "omnibase_core-0.47.72.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: omnibase-core\nVersion: 0.47.72\n",
        )
    (dist / "SHA256SUMS.txt").write_text(_C_SUMS)

    body = tmp_path / "pypi_body.json"
    body.write_text(
        json.dumps(
            {
                "info": {"version": "0.47.72"},
                "urls": [
                    {"filename": _C_WHEEL, "digests": {"sha256": _C_WHEEL_SHA}},
                    {"filename": _C_SDIST, "digests": {"sha256": sdist_sha_on_pypi}},
                ],
            }
        )
    )

    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    for name, text in (
        ("curl", _STUB_CURL_TO_FILE),
        ("sleep", _STUB_SLEEP),
        ("uv", _STUB_UV_RUN_MODULE.format(python=sys.executable)),
    ):
        stub = stub_bin / name
        stub.write_text(text)
        stub.chmod(0o755)

    curl_log = tmp_path / "curl_argv.log"
    curl_log.write_text("")
    uv_log = tmp_path / "uv_argv.log"
    uv_log.write_text("")
    summary = tmp_path / "summary.md"

    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{stub_bin}{os.pathsep}{env['PATH']}",
            "CURL_STUB_ARGV_LOG": str(curl_log),
            "CURL_STUB_BODY": str(body),
            "CURL_STUB_FAIL": "1" if curl_fails else "0",
            "SLEEP_STUB_LOG": str(tmp_path / "sleep.log"),
            "UV_STUB_ARGV_LOG": str(uv_log),
            "GITHUB_STEP_SUMMARY": str(summary),
            "RELEASE_TAG": _C_TAG,
            "PYPI_READ_ATTEMPTS": "2",
        }
    )
    proc = subprocess.run(
        ["bash", "-e", str(script_path)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return _ConsistencyRun(
        returncode=proc.returncode,
        stdout=proc.stdout + proc.stderr,
        curl_invocations=[
            line for line in curl_log.read_text().splitlines() if line.strip()
        ],
        uv_invocations=[
            line for line in uv_log.read_text().splitlines() if line.strip()
        ],
        summary=summary.read_text() if summary.exists() else "",
    )


def test_release_consistency_runs_only_after_a_successful_release() -> None:
    assert _CONSISTENCY_STEP not in {
        str(step.get("name"))
        for name in _jobs()
        if name != _RELEASE_JOB
        for step in _job_steps(_job(str(name)))
    }, "the report is a step of the release job, not a job of its own"
    index = _step_index(_CONSISTENCY_STEP)
    assert index == len(_steps()) - 1, "the report is the release job's last step"
    assert index > _step_index(_MAIN_SYNC_STEP)
    assert index > _step_index(_PUBLISH_STEP)
    step = _step(_CONSISTENCY_STEP)
    # No `if:` means the default success(): it runs only when every earlier
    # step (publish, GitHub Release, main sync) succeeded or was skipped.
    assert "if" not in step, step.get("if")
    assert step.get("continue-on-error") is True


def test_release_consistency_reports_agree_and_ends_green(tmp_path: Path) -> None:
    run = _run_consistency_script(tmp_path, sdist_sha_on_pypi=_C_SDIST_SHA)
    assert run.returncode == 0, run.stdout
    assert "::warning::" not in run.stdout, run.stdout
    assert f"AGREE {_C_SDIST}" in run.stdout
    assert any(
        "https://pypi.org/pypi/omnibase-core/0.47.72/json" in call
        for call in run.curl_invocations
    ), run.curl_invocations
    # The node runs from the wheel this release built, not the checkout.
    assert len(run.uv_invocations) == 1, run.uv_invocations
    assert f"--with dist/{_C_WHEEL}" in run.uv_invocations[0], run.uv_invocations
    assert _CONSISTENCY_MODULE in run.uv_invocations[0], run.uv_invocations
    # AC3's fields: the tag, every published file with its sha256 result, and
    # the metadata version.
    assert _C_TAG in run.summary, run.summary
    for name, sha in ((_C_WHEEL, _C_WHEEL_SHA), (_C_SDIST, _C_SDIST_SHA)):
        assert f"AGREE {name} sha256 {sha}" in run.summary, run.summary
    assert "wheel metadata Version 0.47.72" in run.summary, run.summary


def test_release_consistency_mismatch_warns_and_never_fails_the_release(
    tmp_path: Path,
) -> None:
    run = _run_consistency_script(tmp_path, sdist_sha_on_pypi="0" * 64)
    assert run.returncode == 0, run.stdout
    assert f"MISMATCH {_C_SDIST}" in run.stdout
    assert "::warning::Release consistency MISMATCH" in run.stdout


def test_release_consistency_unreadable_pypi_reads_unknown_after_retries(
    tmp_path: Path,
) -> None:
    run = _run_consistency_script(
        tmp_path, sdist_sha_on_pypi=_C_SDIST_SHA, curl_fails=True
    )
    assert run.returncode == 0, run.stdout
    assert len(run.curl_invocations) == 2, run.curl_invocations
    assert "::warning::Release consistency UNKNOWN" in run.stdout
    assert "MISMATCH" not in run.stdout

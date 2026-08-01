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
* **Behaviour** assertions, which extract the publish step's real ``run:``
  script out of the real workflow file and *execute it* under ``bash -e`` (the
  shell GitHub Actions uses) against a stubbed ``uv``/``sleep`` on ``PATH``.
  Nothing is re-implemented here -- a regression in the committed shell is a
  regression in these tests.
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


def _release_job() -> dict[object, object]:
    jobs = _as_mapping(_workflow()["jobs"], "release.yml `jobs:`")
    return _as_mapping(jobs["release"], "the `release` job")


def _steps() -> list[dict[object, object]]:
    steps = _release_job()["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _step_index(name: str) -> int:
    for index, step in enumerate(_steps()):
        if step.get("name") == name:
            return index
    raise AssertionError(f"release job must have a step named {name!r}")


def _step(name: str) -> dict[object, object]:
    return _steps()[_step_index(name)]


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
  echo "Server returned status code 500 Internal Server Error" >&2
  exit 1
fi
echo "Uploaded ok"
exit 0
"""

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


def _run_publish_script(tmp_path: Path, *, fail_times: int) -> _PublishRun:
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


def test_partial_release_state_is_reported_loudly_on_failure() -> None:
    """AC4: a stranded release must name which artifacts landed."""
    step = _step(_PARTIAL_STATE_STEP)

    assert str(step["if"]).strip() == "failure()"
    assert _step_index(_PARTIAL_STATE_STEP) > _step_index(_RELEASE_STEP)

    run = str(step["run"])
    assert "::error::" in run
    assert "RELEASE INCOMPLETE" in run
    assert "LANDED on PyPI" in run
    assert "MISSING from PyPI" in run
    assert "gh workflow run release.yml" in run


def test_dependency_cascade_still_runs_off_the_release_output() -> None:
    """AC4 regression guard: the cascade wiring must survive the reorder."""
    jobs = _as_mapping(_workflow()["jobs"], "release.yml `jobs:`")
    cascade = _as_mapping(jobs["dependency-cascade"], "the `dependency-cascade` job")

    assert cascade["needs"] == "release"
    assert "./.github/workflows/dependency-cascade.yml" in str(cascade["uses"])
    assert _release_job()["outputs"] == {"version": "${{ steps.tag.outputs.tag }}"}


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
    assert tag_input["required"] is True

    checkout = _steps()[0]
    assert "actions/checkout@" in str(checkout["uses"])
    ref = str(_as_mapping(checkout["with"], "checkout `with:`")["ref"])
    assert "workflow_dispatch" in ref
    assert "inputs.tag" in ref

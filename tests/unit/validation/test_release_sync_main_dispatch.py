# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shape + behaviour gate for the sync-only main fast-forward (OMN-16289).

`main` = the last release. The fast-forward that makes that true is the LAST
step of `release.yml`'s `release` job, sequenced behind `Publish to PyPI` and
`Create GitHub Release`. When only that step fails -- as it did on runs 34030901325 (v0.47.4) and 34052816626 (v0.47.5),
where publish and the GitHub Release both succeeded and
`Mint onexbot-occ-writer app token` returned HTTP 422 because the App
installation had not been granted `workflows: write` -- there was no way to
complete the pointer move. `gh run rerun --failed` re-runs the WHOLE job
including the publish, and so does a plain `-f tag=` dispatch, which also
re-cuts the GitHub Release and re-fires every downstream job. Every recovery
path went through a re-publish, so `main` simply stayed stale.

`sync_main_to_tag` is the path that does not. The tests below are split the way
this repo's release-workflow tests already are:

* **Shape** assertions parse the real workflow YAML -- the job graph, the job
  conditions, and the fact that the sync-only job builds and publishes nothing.
* **Behaviour** assertions extract the real `Validate sync tag` script out of
  the committed workflow and EXECUTE it under `bash -e` against a real
  throwaway git repository with a real `origin`. Nothing is re-implemented
  here: a regression in the committed shell is a regression in these tests.
  That is also why the script must stay free of inline `${{ }}` expressions
  (values arrive through `env:`) -- an expression would make the committed
  shell unrunnable here and quietly turn these tests into string matching.

The two guards under test are both fail-closed: the tag must be an ancestor of
`origin/dev` (it is a release cut from dev, not from anywhere else), and
`origin/main` must be an ancestor of the tag (the move is a fast-forward, never
backwards or sideways). `main` already at the tag is a no-op, not a failure, so
a re-dispatch of an already-synced tag is safe.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

RELEASE_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "release.yml"
)

_SYNC_JOB = "sync-main"
_RELEASE_JOB = "release"
_CASCADE_JOB = "dependency-cascade"
_VALIDATE_STEP = "Validate sync tag"
_MINT_STEP = "Mint onexbot-occ-writer app token"
_SYNC_STEP = "Sync main to release tag"
_SYNC_INPUT = "sync_main_to_tag"


# --------------------------------------------------------------------------
# workflow parsing helpers
# --------------------------------------------------------------------------
def _workflow() -> dict[Any, Any]:
    loaded = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _triggers() -> dict[Any, Any]:
    """YAML 1.1 parses a bare ``on:`` key as the boolean ``True``."""
    workflow = _workflow()
    key: Any = True if True in workflow else "on"
    triggers = workflow[key]
    assert isinstance(triggers, dict)
    return triggers


def _job(name: str) -> dict[Any, Any]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    assert name in jobs, f"release.yml must define a `{name}` job; has {list(jobs)}"
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _steps(job_name: str) -> list[dict[Any, Any]]:
    steps = _job(job_name)["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _step(job_name: str, step_name: str) -> dict[Any, Any]:
    for step in _steps(job_name):
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"job `{job_name}` must have a step named {step_name!r}")


def _validate_script() -> str:
    run = _step(_SYNC_JOB, _VALIDATE_STEP)["run"]
    assert isinstance(run, str)
    return run


# --------------------------------------------------------------------------
# shape
# --------------------------------------------------------------------------
def test_sync_only_dispatch_input_exists_and_is_optional() -> None:
    """The recovery input must not be required, or every release dispatch needs it."""
    inputs = _triggers()["workflow_dispatch"]["inputs"]
    assert _SYNC_INPUT in inputs, (
        "release.yml has no `sync_main_to_tag` input -- the only way to finish a "
        "main fast-forward would be re-running the publish (OMN-16289)"
    )
    assert inputs[_SYNC_INPUT].get("required") is not True
    assert inputs[_SYNC_INPUT].get("default", "") == ""


def test_release_tag_input_is_optional_so_a_sync_only_dispatch_can_omit_it() -> None:
    inputs = _triggers()["workflow_dispatch"]["inputs"]
    assert inputs["tag"].get("required") is not True
    assert inputs["tag"].get("default", "") == ""


def test_a_sync_only_dispatch_skips_the_release_job_entirely() -> None:
    """This is the whole point: no re-publish, no re-cut GitHub Release."""
    condition = str(_job(_RELEASE_JOB)["if"])
    assert f"inputs.{_SYNC_INPUT} == ''" in condition, condition
    assert "workflow_dispatch" in condition, condition


def test_the_sync_job_only_runs_for_a_sync_only_dispatch() -> None:
    condition = str(_job(_SYNC_JOB)["if"])
    assert "github.event_name == 'workflow_dispatch'" in condition, condition
    assert f"inputs.{_SYNC_INPUT} != ''" in condition, condition


def test_the_sync_job_builds_and_publishes_nothing() -> None:
    """A recovery path that can publish is not a recovery path."""
    body = yaml.safe_dump(_job(_SYNC_JOB))
    for forbidden in (
        "uv build",
        "uv publish",
        "publish_with_retry",
        "action-gh-release",
    ):
        assert forbidden not in body, (
            f"the sync-only job must not contain {forbidden!r}"
        )


def test_the_sync_job_keeps_the_release_jobs_step_names() -> None:
    """OMN-18010 (release-on-merge) reuses this path and reads these names."""
    names = [step.get("name") for step in _steps(_SYNC_JOB)]
    assert _MINT_STEP in names, names
    assert _SYNC_STEP in names, names
    assert names.index(_MINT_STEP) < names.index(_SYNC_STEP), names


def test_the_sync_updates_the_ref_over_rest_with_the_minted_app_token() -> None:
    """The main ruleset's only bypass actor is the onexbot-occ-writer App.

    The pointer move must NOT go over git. actions/checkout v7 persists the
    workflow GITHUB_TOKEN as an ``http.<origin>.extraheader`` written into a
    separate file and pulled in through ``includeIf.gitdir`` -- NOT into
    ``--local`` config. The OMN-17272 mitigation
    (``git config --local --unset-all http.https://github.com/.extraheader``)
    therefore removes nothing, the included header still overrides credentials
    embedded in a remote URL, and the push authenticates as
    ``github-actions[bot]``. The ruleset declines exactly that, with GH013
    "Cannot update this protected ref" -- reproduced live on core runs
    34065670492 and 34069756070 (2026-09-06): mint SUCCESS, sync FAILURE.

    Updating ``refs/heads/main`` through the REST API with the App token has
    no git credential layer that could override the identity. That is the
    shape omnimarket already syncs main with, live-proven against its ACTIVE
    ruleset (run 34050376661, main = v0.4.18).
    """
    for job in (_SYNC_JOB, _RELEASE_JOB):
        script = str(_step(job, _SYNC_STEP)["run"])

        # The token must never travel through a git remote URL again.
        assert "access-token:" not in script, (job, script)
        assert "git push" not in script, (job, script)

        assert "-X PATCH" in script, (job, script)
        assert (
            "${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/git/refs/heads/main" in script
        ), (job, script)
        assert "Authorization: Bearer ${APP_TOKEN}" in script, (job, script)

        # Server-side fast-forward enforcement, on top of this workflow's own
        # ancestry guard. A forced ref update would defeat both.
        assert '"force":false' in script, (job, script)
        assert "--force" not in script, (job, script)

        # A non-2xx ref update must fail the step, not be swallowed.
        assert "http_code" in script, (job, script)


def test_the_sync_app_token_can_write_refs_and_tagged_workflows() -> None:
    """Both scopes, because a ``permission-*`` input REPLACES the whole set.

    ``actions/create-github-app-token`` does not ADD to the installation's
    permissions when a ``permission-*`` input is present -- it narrows the
    minted token to exactly what is listed. Listing only
    ``permission-workflows: write`` therefore drops ``contents: write``, and a
    token with no contents scope cannot move ``refs/heads/main`` at all: run
    34065670492 (v0.47.5) minted successfully and then died on
    ``GH013 ... Cannot update this protected ref``, which reads exactly like a
    ruleset rejection of the identity. omnimarket, whose sync has worked
    throughout, mints with ``permission-contents: write``.
    """
    for job in (_SYNC_JOB, _RELEASE_JOB):
        # The release job's mint step carries a repo-specific suffix in some
        # repos, so resolve it by `id` rather than by exact name; the sync-only
        # job's names are the ones OMN-18010 reads and those stay canonical.
        mint = next(step for step in _steps(job) if step.get("id") == "app-token")
        with_block = mint["with"]
        assert isinstance(with_block, dict)
        assert with_block["permission-contents"] == "write", (
            f"the {job} job's main-sync App token has no contents scope, so the "
            "fast-forward push is rejected before the ruleset is even consulted"
        )
        assert with_block["permission-workflows"] == "write", (
            f"the {job} job's main-sync App token cannot fast-forward a release "
            "tag that changes .github/workflows/**"
        )


def test_the_mint_and_push_steps_are_skipped_when_main_is_already_synced() -> None:
    for step_name in (_MINT_STEP, _SYNC_STEP):
        condition = str(_step(_SYNC_JOB, step_name)["if"])
        assert "steps.sync_tag.outputs.noop == 'false'" in condition, condition


def test_the_validate_script_carries_no_inline_expressions() -> None:
    """Otherwise the behaviour tests below silently become string matching."""
    assert "${{" not in _validate_script()


def test_a_skipped_release_job_cannot_fire_the_dependency_cascade() -> None:
    condition = str(_job(_CASCADE_JOB)["if"])
    assert "needs.release.result == 'success'" in condition, condition


# --------------------------------------------------------------------------
# behaviour harness: run the REAL validate script against a REAL git repo
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class _ValidateRun:
    returncode: int
    stdout: str
    stderr: str
    outputs: dict[str, str]


def _git(cwd: Path, *args: str) -> str:
    """Run git against ``cwd`` only.

    ``env=scrub_git_location_env(...)`` is not optional (OMN-14891): git exports
    GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE into every hook environment and
    those OVERRIDE both ``cwd=`` and ``-C``, so an unscrubbed fixture run under
    a pre-commit or pre-push hook mutates the REAL worktree instead of tmp_path.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(os.environ),
    )
    return result.stdout.strip()


def _build_fixture_repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A clone with a real ``origin``, three dev commits and a side branch.

    Returns the working clone and a map of logical name -> commit SHA.
    """
    upstream = tmp_path / "upstream.git"
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=dev", str(upstream)],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(os.environ),
    )

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "--initial-branch=dev")
    _git(seed, "config", "user.email", "test@example.invalid")
    _git(seed, "config", "user.name", "test")

    shas: dict[str, str] = {}
    for name in ("c1", "c2", "c3"):
        (seed / f"{name}.txt").write_text(name)
        _git(seed, "add", ".")
        _git(seed, "commit", "-m", name)
        shas[name] = _git(seed, "rev-parse", "HEAD")

    # A tag on dev lineage, and a tag on a branch that never reached dev.
    _git(seed, "tag", "v1.0.0", shas["c2"])
    _git(seed, "tag", "v9.9.9-rc1", shas["c2"])
    _git(seed, "checkout", "-q", "-b", "sidebranch", shas["c1"])
    (seed / "side.txt").write_text("side")
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", "side")
    shas["side"] = _git(seed, "rev-parse", "HEAD")
    _git(seed, "tag", "v2.0.0", shas["side"])
    _git(seed, "checkout", "-q", "dev")

    _git(seed, "branch", "main", shas["c1"])
    _git(seed, "remote", "add", "origin", str(upstream))
    _git(seed, "push", "-q", "origin", "dev", "main", "sidebranch", "--tags")

    work = tmp_path / "work"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(work)],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(os.environ),
    )
    return work, shas


def _set_upstream_main(work: Path, sha: str) -> None:
    _git(work, "push", "-q", "--force", "origin", f"{sha}:refs/heads/main")


def _run_validate(tmp_path: Path, work: Path, sync_tag: str) -> _ValidateRun:
    script = tmp_path / "validate_sync_tag.sh"
    script.write_text(_validate_script())
    github_output = tmp_path / "github_output"
    github_output.write_text("")

    env = scrub_git_location_env(os.environ)
    env.update(
        {
            "SYNC_TAG": sync_tag,
            "GITHUB_OUTPUT": str(github_output),
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    result = subprocess.run(
        ["bash", "-e", str(script)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    outputs: dict[str, str] = {}
    for line in github_output.read_text().splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            outputs[key] = value
    return _ValidateRun(result.returncode, result.stdout, result.stderr, outputs)


def test_validate_accepts_a_dev_ancestor_tag_ahead_of_main(tmp_path: Path) -> None:
    work, shas = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "v1.0.0")
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.outputs["noop"] == "false", run.outputs
    assert run.outputs["tag"] == "v1.0.0", run.outputs
    assert run.outputs["tag_sha"] == shas["c2"], run.outputs


def test_validate_reports_a_noop_when_main_is_already_at_the_tag(
    tmp_path: Path,
) -> None:
    """A re-dispatch of an already-synced tag must not fail the run."""
    work, shas = _build_fixture_repo(tmp_path)
    _set_upstream_main(work, shas["c2"])
    run = _run_validate(tmp_path, work, "v1.0.0")
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.outputs["noop"] == "true", run.outputs


def test_validate_refuses_to_move_main_backwards(tmp_path: Path) -> None:
    work, shas = _build_fixture_repo(tmp_path)
    _set_upstream_main(work, shas["c3"])
    run = _run_validate(tmp_path, work, "v1.0.0")
    assert run.returncode != 0, run.stdout
    assert "backwards" in run.stdout + run.stderr
    assert "noop" not in run.outputs, run.outputs


def test_validate_refuses_a_tag_that_is_not_an_ancestor_of_dev(
    tmp_path: Path,
) -> None:
    work, _ = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "v2.0.0")
    assert run.returncode != 0, run.stdout
    assert "not an ancestor of origin/dev" in run.stdout + run.stderr


def test_validate_refuses_a_tag_that_does_not_exist(tmp_path: Path) -> None:
    work, _ = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "v3.1.4")
    assert run.returncode != 0, run.stdout
    assert "does not exist" in run.stdout + run.stderr


def test_validate_refuses_a_prerelease_tag(tmp_path: Path) -> None:
    work, _ = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "v9.9.9-rc1")
    assert run.returncode != 0, run.stdout
    assert "prerelease" in run.stdout + run.stderr


def test_validate_refuses_a_non_release_tag_shape(tmp_path: Path) -> None:
    work, _ = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "dev")
    assert run.returncode != 0, run.stdout
    assert "not a vX.Y.Z release tag" in run.stdout + run.stderr


def test_validate_refuses_an_empty_input(tmp_path: Path) -> None:
    work, _ = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "")
    assert run.returncode != 0, run.stdout


def test_validate_refuses_an_input_that_would_forge_extra_step_outputs(
    tmp_path: Path,
) -> None:
    """A newline in the dispatch input must never reach GITHUB_OUTPUT."""
    work, _ = _build_fixture_repo(tmp_path)
    run = _run_validate(tmp_path, work, "v1.0.0\nnoop=true")
    assert run.returncode != 0, run.stdout
    assert "unsupported characters" in run.stdout + run.stderr
    assert run.outputs == {}, run.outputs

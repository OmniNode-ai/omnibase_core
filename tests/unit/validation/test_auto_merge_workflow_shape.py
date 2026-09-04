# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "auto-merge.yml"
)


def _steps() -> list[dict[str, object]]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return data["jobs"]["auto-merge"]["steps"]


def _step(name: str) -> dict[str, object]:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"{name!r} step not found in auto-merge.yml")


def _job() -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return data["jobs"]["auto-merge"]


def test_auto_merge_job_requires_occ_preflight_success() -> None:
    # OMN-16288: the auto-merge job trusts the already-required
    # "occ-preflight / eligibility" check's conclusion (resolved from the PR
    # body's Evidence-Source pin by the shared occ-preflight.yml reusable --
    # the same pattern omnibase_infra/omnimarket use) instead of re-resolving
    # OCC eligibility itself. It must not run any step before that gate is
    # satisfied.
    job = _job()

    assert "occ-preflight" in job["needs"]
    assert "needs.occ-preflight.result == 'success'" in job["if"]


def test_auto_merge_does_not_re_resolve_occ_against_heads_main() -> None:
    # Regression guard for OMN-16288: this job previously re-resolved OCC
    # eligibility by fetching onex_change_control@heads/main and re-running
    # validator_occ_merge_eligibility against that checkout. Nothing promotes
    # OCC's own contracts dev->main (OMN-15067), so OCC main is thousands of
    # commits stale and that duplicate check failed permanently
    # (eligible:false/missing_contract, e.g. OMN-16280 / run 32359138410) --
    # it never gated arming (the job-level needs/if above already did), it
    # only ever broke it. It must not come back.
    names = [step.get("name") for step in _steps()]

    assert "Resolve OCC main SHA" not in names
    assert "Check out OCC evidence snapshot" not in names
    assert "OCC auto-merge preflight" not in names
    assert "Set up Python 3.13" not in names

    for step in _steps():
        run = step.get("run", "")
        if isinstance(run, str):
            assert "onex_change_control/git/ref/heads/main" not in run
            assert "validator_occ_merge_eligibility" not in run


def test_enable_auto_merge_tries_bare_auto_first() -> None:
    # OMN-13214: on a queue-controlled branch an explicit --squash is
    # rejected and the PR is never enqueued. The FIRST `gh pr merge` attempt
    # must still arm bare --auto so that regime keeps working if a queue
    # reappears (queue picks the method, then the enqueue+verify step below
    # calls enqueuePullRequest explicitly).
    script = _step("Enable auto-merge")["run"]
    assert isinstance(script, str)
    assert 'gh pr merge "$PR" --repo "$GH_REPO" --auto 2>&1' in script


def test_enable_auto_merge_retries_with_squash_on_no_queue_error_only() -> None:
    # OMN-16507: same defect class as OMN-16501 (omniclaude, Done) -- dev is
    # NOT currently queue-controlled (registry-wide verify 2026-08-24), and
    # gh's CLI refuses a method-less --auto non-interactively even on this
    # verified squash-only repo ("--merge, --rebase, or --squash required
    # when not running interactively"), red on every PR (e.g.
    # omnibase_core#1588, OMN-16347). The step must retry with --squash (the
    # repo's one enabled method) gated on that SPECIFIC gh-CLI error string,
    # so a genuine queue-controlled rejection ("merge strategy ... set by the
    # merge queue") is a distinct error and is never retried with an
    # explicit method.
    script = _step("Enable auto-merge")["run"]
    assert isinstance(script, str)
    assert 'gh pr merge "$PR" --repo "$GH_REPO" --auto --squash 2>&1' in script
    assert "required when not running interactively" in script


def test_enqueue_step_classifies_enqueues_and_verifies() -> None:
    # OMN-13214: arming != enqueuing. The enqueue step must classify via the
    # unit-tested helper, explicitly enqueue, and VERIFY the PR entered the queue.
    script = _step("Enqueue armed PR and verify it entered the queue")["run"]

    assert "scripts/ci/merge_queue_enqueue.py classify" in script
    assert "scripts/ci/merge_queue_enqueue.py verify" in script
    assert "enqueuePullRequest" in script
    assert "gh pr update-branch" in script
    # Must fail loudly when a green + armed PR does not enter the queue.
    assert "::error::" in script


@pytest.fixture
def gh_merge_stub_dir(tmp_path: Path) -> Path:
    """Stub ``gh`` CLI for the ``Enable auto-merge`` step's two possible
    ``gh pr merge`` invocations (bare ``--auto`` and the ``--auto --squash``
    fallback), each independently scripted to succeed or fail via env vars.
    """
    stub = tmp_path / "gh"
    stub.write_text(
        dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            args="$*"
            case "$args" in
              *"--auto --squash"*)
                if [ "${STUB_SQUASH_RESULT:-success}" = "success" ]; then
                  echo "${STUB_SQUASH_OUTPUT:-auto-merge enabled}"
                  exit 0
                else
                  echo "${STUB_SQUASH_OUTPUT:-squash attempt failed}" >&2
                  exit 1
                fi
                ;;
              *"--auto"*)
                if [ "${STUB_BARE_RESULT:-success}" = "success" ]; then
                  echo "${STUB_BARE_OUTPUT:-auto-merge enabled}"
                  exit 0
                else
                  echo "${STUB_BARE_OUTPUT:-bare attempt failed}" >&2
                  exit 1
                fi
                ;;
              *)
                echo "unexpected gh invocation: $args" >&2
                exit 99
                ;;
            esac
            """
        )
    )
    stub.chmod(0o755)
    return tmp_path


def _run_enable_auto_merge(
    *,
    gh_merge_stub_dir: Path,
    bare_result: str = "success",
    bare_output: str = "",
    squash_result: str = "success",
    squash_output: str = "",
) -> subprocess.CompletedProcess[str]:
    """Run the live ``Enable auto-merge`` Bash (extracted straight from the
    YAML via ``_step``, so the tests are bound to the deployed logic, not a
    re-implementation of it) against the stubbed ``gh``.
    """
    script = _step("Enable auto-merge")["run"]
    assert isinstance(script, str)
    env = {
        "PATH": f"{gh_merge_stub_dir}:/usr/bin:/bin",
        "GH_TOKEN": "stub-token",
        "GH_REPO": "OmniNode-ai/omnibase_core",
        "PR": "1588",
        "STUB_BARE_RESULT": bare_result,
        "STUB_BARE_OUTPUT": bare_output,
        "STUB_SQUASH_RESULT": squash_result,
        "STUB_SQUASH_OUTPUT": squash_output,
    }
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class TestAutoMergeEnableStepBehavior:
    """Behavioral coverage for the ``Enable auto-merge`` step's retry logic
    (OMN-16507, mirrors OMN-16501). Extracts the live Bash from the YAML so
    the tests are bound to the deployed logic, not a re-implementation of
    it."""

    def test_bare_auto_success_does_not_retry(self, gh_merge_stub_dir: Path) -> None:
        """Queue-controlled regime (OMN-13214): bare --auto succeeding must
        not trigger the --squash fallback at all."""
        result = _run_enable_auto_merge(
            gh_merge_stub_dir=gh_merge_stub_dir,
            bare_result="success",
            bare_output="Auto-merge enabled",
        )
        assert result.returncode == 0, result.stderr
        assert "auto-merge enabled:" in result.stdout
        assert "(squash)" not in result.stdout

    def test_already_enqueued_is_benign_no_retry(self, gh_merge_stub_dir: Path) -> None:
        """A benign 'already enqueued' race must exit 0 without invoking the
        --squash retry (the squash stub is set to fail, proving it was never
        called)."""
        result = _run_enable_auto_merge(
            gh_merge_stub_dir=gh_merge_stub_dir,
            bare_result="failure",
            bare_output="pull request already enqueued",
            squash_result="failure",
            squash_output="must not be invoked",
        )
        assert result.returncode == 0, result.stderr
        assert "not newly enabled (expected)" in result.stdout

    def test_no_active_queue_retries_with_squash(self, gh_merge_stub_dir: Path) -> None:
        """OMN-16507 reproduction (omnibase_core#1588, same class as
        OMN-16501): bare --auto rejected non-interactively (no active merge
        queue) must retry with --squash and succeed."""
        result = _run_enable_auto_merge(
            gh_merge_stub_dir=gh_merge_stub_dir,
            bare_result="failure",
            bare_output=(
                "--merge, --rebase, or --squash required when not running interactively"
            ),
            squash_result="success",
            squash_output="Auto-merge enabled",
        )
        assert result.returncode == 0, result.stderr
        assert "bare --auto rejected" in result.stdout
        assert "auto-merge enabled (squash):" in result.stdout

    def test_squash_retry_failure_still_propagates(
        self, gh_merge_stub_dir: Path
    ) -> None:
        """If the --squash retry itself fails for a real reason, the step
        must still fail loudly rather than swallow the error."""
        result = _run_enable_auto_merge(
            gh_merge_stub_dir=gh_merge_stub_dir,
            bare_result="failure",
            bare_output=(
                "--merge, --rebase, or --squash required when not running interactively"
            ),
            squash_result="failure",
            squash_output="some unrelated permanent error",
        )
        assert result.returncode == 1
        assert "auto-merge failed:" in result.stdout

    def test_queue_controlled_rejection_is_not_retried_with_squash(
        self, gh_merge_stub_dir: Path
    ) -> None:
        """A genuine queue-controlled rejection ('merge strategy ... set by
        the merge queue') is a DIFFERENT error than gh's non-interactive
        method requirement and must NOT trigger the --squash retry — passing
        an explicit method on a queue-controlled branch is itself rejected
        (OMN-13214). The squash stub is set to succeed, proving it was never
        reached."""
        result = _run_enable_auto_merge(
            gh_merge_stub_dir=gh_merge_stub_dir,
            bare_result="failure",
            bare_output="The merge strategy for dev is set by the merge queue",
            squash_result="success",
        )
        assert result.returncode == 1
        assert "auto-merge failed:" in result.stdout
        assert "(squash)" not in result.stdout


# ---------------------------------------------------------------------------
# OMN-17875: arming-token guard.
#
# Root cause (measured live 2026-09-04T15:20-15:25Z on this repo): the two
# merge-state-mutating steps armed `gh pr merge --auto` with
# `secrets.GITHUB_TOKEN`. GitHub completes an armed auto-merge as the identity
# that armed it, and fires no `push` event for `GITHUB_TOKEN`-authored commits
# (documented Actions-recursion prevention). Every push-on-`dev` workflow was
# therefore skipped on every PR that landed through this job::
#
#     1bd884e57 (#1645, app/github-actions) -> 0 push runs
#     d191ffb22 (#1643, jonahgabriel)       -> 12 push runs
#
# (`gh api "repos/OmniNode-ai/omnibase_core/actions/runs?head_sha=<full-oid>&event=push"
# --jq .total_count`.) Over the 30 most recently merged dev PRs, ALL 20 bot
# merges had zero dev-branch push runs while all 10 human merges had 12-14 --
# the human counts are the positive control that makes those zeros evidence of
# absence rather than a broken query (CLAUDE.md rule 16).
#
# Fix: arm with `secrets.CROSS_REPO_PAT` -- an existing org secret
# (`visibility: all`) this repo already consumes in seven other workflows, and
# the same credential omninode_infra's auto-merge.yml deliberately retained for
# this exact property (OMN-15769, re-affirmed by OMN-16373). Ported from
# omnibase_infra#3178.
#
# These assertions are the mechanical guard (CLAUDE.md rule 5: enforcement, not
# detection) so the swap cannot be silently reverted to `GITHUB_TOKEN` -- or
# "modernised" to an `onexbot-occ-writer` App installation token, which the
# OMN-16373 controlled probe proved suppresses push events identically.
# ---------------------------------------------------------------------------

# The steps that cause a commit to be attributed to the token: arming the
# merge, and update-branch/enqueue. Both must carry the non-suppressing
# identity.
MUTATING_STEP_NAMES: tuple[str, ...] = (
    "Enable auto-merge",
    "Enqueue armed PR and verify it entered the queue",
)

# The step that only reads PR/repo metadata. It lives in the `pre-check` job,
# not `auto-merge`, and is safe under the default token because it creates no
# commit.
READ_ONLY_STEP_JOB = "pre-check"
READ_ONLY_STEP_NAME = "Resolve PR number and author without checkout"

REQUIRED_TOKEN_EXPR = "${{ secrets.CROSS_REPO_PAT }}"

# Substrings that would reintroduce the suppression on a different credential.
APP_TOKEN_MARKERS: tuple[str, ...] = (
    "create-github-app-token",
    "ONEXBOT_OCC_APP_ID",
    "ONEXBOT_OCC_PRIVATE_KEY",
)


def _step_in_job(job_name: str, step_name: str) -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = data["jobs"][job_name]["steps"]
    matches = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == step_name
    ]
    assert len(matches) == 1, (
        f"expected exactly one step named {step_name!r} in job {job_name!r}, "
        f"got {len(matches)}"
    )
    return matches[0]


@pytest.mark.parametrize("step_name", MUTATING_STEP_NAMES)
def test_merge_state_mutating_steps_arm_with_cross_repo_pat(step_name: str) -> None:
    """The arming/enqueue steps must authenticate as CROSS_REPO_PAT.

    A GITHUB_TOKEN- or App-token-authored merge commit fires no push event, so
    this assertion is the difference between ci.yml / security-scan.yml /
    cross-repo-validation.yml (and nine more) running on every dev merge and
    running on none of them.
    """
    step = _step_in_job("auto-merge", step_name)
    env = step.get("env")
    assert isinstance(env, dict)
    token = env.get("GH_TOKEN")
    assert token == REQUIRED_TOKEN_EXPR, (
        f"{step_name!r} must arm with {REQUIRED_TOKEN_EXPR}; found {token!r}. "
        "GITHUB_TOKEN- and GitHub-App-token-authored merges suppress "
        "push-triggered workflow runs on dev (OMN-17875 / OMN-16373)."
    )


@pytest.mark.parametrize("step_name", MUTATING_STEP_NAMES)
def test_mutating_steps_have_no_github_token_fallback(step_name: str) -> None:
    """No ``|| secrets.GITHUB_TOKEN`` fallback on the mutating steps.

    A fallback would restore the defect silently on any run where the PAT is
    unavailable, which is exactly the invisible-failure shape this ticket
    exists to remove: the job would report success while starving every
    downstream push workflow.
    """
    step = _step_in_job("auto-merge", step_name)
    env = step.get("env")
    assert isinstance(env, dict)
    token = str(env.get("GH_TOKEN", ""))
    assert "GITHUB_TOKEN" not in token, (
        f"{step_name!r} must not fall back to GITHUB_TOKEN; found {token!r}"
    )


def test_read_only_resolve_step_stays_on_default_token() -> None:
    """The read-only ``pre-check`` step keeps GITHUB_TOKEN — it creates no commit.

    Narrow blast radius is deliberate: the PAT is only granted to the steps
    that actually need the non-suppressing identity.
    """
    step = _step_in_job(READ_ONLY_STEP_JOB, READ_ONLY_STEP_NAME)
    env = step.get("env")
    assert isinstance(env, dict)
    assert env.get("GH_TOKEN") == "${{ secrets.GITHUB_TOKEN }}"

    run = step.get("run", "")
    assert isinstance(run, str)
    for mutating_verb in (
        "gh pr merge",
        "gh pr update-branch",
        "enqueuePullRequest",
        "git push",
    ):
        assert mutating_verb not in run, (
            f"{READ_ONLY_STEP_NAME!r} performs {mutating_verb!r} but runs under "
            "GITHUB_TOKEN; move it to a CROSS_REPO_PAT step or the suppression "
            "returns."
        )


def test_no_app_token_mint_is_introduced() -> None:
    """An onexbot-occ-writer App token is not a valid substitute here.

    The OMN-16373 controlled probe pushed commit ``38ffe1f4`` under the App
    identity and the push-triggered marker workflow did not fire, while the
    ``jonahgabriel`` control push (``fd534b2a``) fired run 32562988366.
    """
    raw = WORKFLOW_PATH.read_text()
    body = raw.split("name: Auto-Merge", 1)[1]
    for marker in APP_TOKEN_MARKERS:
        assert marker not in body, (
            f"auto-merge.yml must not mint a GitHub App token ({marker!r}); "
            "App-token pushes suppress push-triggered runs identically to "
            "GITHUB_TOKEN (OMN-16373)."
        )


def test_header_documents_the_defect_and_cites_the_evidence_tickets() -> None:
    """The in-file rationale must survive, so the next reader does not revert it."""
    header = WORKFLOW_PATH.read_text().split("name: Auto-Merge", 1)[0]
    for citation in ("OMN-17875", "OMN-16373", "CROSS_REPO_PAT"):
        assert citation in header, f"auto-merge.yml header must cite {citation}"

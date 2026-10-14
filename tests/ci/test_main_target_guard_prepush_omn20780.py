# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A push to ``main`` warns locally, and the hosted guard refuses a PR onto ``main`` (OMN-20780).

The operator ruling of 2026-10-10T16:52:56Z re-affirms the standing rule: ``dev``
is the default branch of every code repository and a pull request that targets
``main`` violates it. The hosted ``main-target-guard`` check refuses such a pull
request. A pull request's base is not known at push time, so the one local
signal is the remote ref being pushed, which pre-commit exports as
``PRE_COMMIT_REMOTE_BRANCH`` at the pre-push stage. The ``main-target-guard``
pre-push hook warns on a push to ``main`` and exits 0: the hosted check is the
refusal. This module pins both halves:

* the pre-push hook is wired, warns on ``refs/heads/main`` and prints nothing
  for any other ref (``refs/heads/main-notes`` included);
* the guard's shipped step, run as a program, refuses a feature branch onto
  ``main`` and admits the same branch onto ``dev`` (the negative control).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main-target-guard.yml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"

GUARD_JOB = "main-target-guard"
GUARD_STEP = "Check PR target branch"
GUARD_HOOK_ID = "main-target-guard"


def _guard_program() -> str:
    """The shipped guard step's ``run`` script, exactly as the workflow carries it."""
    workflow = yaml.safe_load(GUARD_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"][GUARD_JOB]["steps"]
    named = [step for step in steps if step.get("name") == GUARD_STEP]
    assert len(named) == 1, f"expected exactly one step named {GUARD_STEP!r}"
    return str(named[0]["run"])


def _run_guard(base: str, head: str) -> subprocess.CompletedProcess[str]:
    """Run the guard the way Actions does: ``bash -e`` over the step script."""
    env = {
        "PATH": os.defpath,
        "BASE_REF": base,
        "HEAD_REF": head,
        "PR_BODY": "",
    }
    return subprocess.run(
        ["bash", "-e", "-c", _guard_program()],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_guard_job_reports_the_required_context_name() -> None:
    workflow = yaml.safe_load(GUARD_WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["jobs"][GUARD_JOB]["name"] == GUARD_JOB


def test_a_feature_pr_onto_main_is_refused() -> None:
    result = _run_guard("main", "feature/OMN-1-thing")
    assert result.returncode != 0, (
        f"a feature PR onto main was admitted:\n{result.stdout}"
    )
    assert "::error::" in result.stdout
    assert "dev" in result.stdout, "the refusal must name dev as the base to use"


def test_a_feature_pr_onto_dev_is_admitted() -> None:
    """The negative control: a guard that refused everything would fail here."""
    result = _run_guard("dev", "feature/OMN-1-thing")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "::error::" not in result.stdout


def _guard_hook() -> dict[str, Any]:
    config: dict[str, Any] = yaml.safe_load(
        PRECOMMIT_CONFIG.read_text(encoding="utf-8")
    )
    hooks: list[dict[str, Any]] = [
        hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook["id"] == GUARD_HOOK_ID
    ]
    assert len(hooks) == 1, f"expected one pre-commit hook with id {GUARD_HOOK_ID!r}"
    return hooks[0]


def _run_hook(remote_branch: str | None) -> subprocess.CompletedProcess[str]:
    """Run the hook's entry the way pre-commit does at the pre-push stage."""
    env = {"PATH": os.defpath}
    if remote_branch is not None:
        env["PRE_COMMIT_REMOTE_BRANCH"] = remote_branch
    return subprocess.run(
        ["bash", "-c", _guard_hook()["entry"]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_pre_push_hook_is_wired_to_warn_and_not_to_fail() -> None:
    hook = _guard_hook()
    assert hook["stages"] == ["pre-push"]
    assert hook["always_run"] is True
    assert hook["pass_filenames"] is False
    assert hook["verbose"] is True, "pre-commit prints a passing hook only when verbose"


def test_a_push_to_main_warns_locally_and_does_not_block() -> None:
    result = _run_hook("refs/heads/main")
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "main-target-guard" in output
    assert "dev" in output


@pytest.mark.parametrize(
    "remote_branch",
    [
        pytest.param("refs/heads/dev", id="dev"),
        pytest.param("refs/heads/feature/OMN-1-thing", id="feature"),
        pytest.param("refs/heads/main-notes", id="main-prefix"),
        pytest.param(None, id="variable-unset"),
    ],
)
def test_a_push_elsewhere_prints_nothing(remote_branch: str | None) -> None:
    result = _run_hook(remote_branch)
    assert result.returncode == 0
    assert (result.stdout + result.stderr).strip() == ""

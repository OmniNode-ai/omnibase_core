# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20940: omnibase_core produces the required context `public-repo-hygiene / deployment-config`.

No deployment or lab configuration lives in a shipped repository, and the check
that refuses it is a required CI context on every shipped repository. omniclaude
ships the check as the ``deployment-config`` job of its reusable hygiene workflow
and as the exported ``deployment-config`` pre-commit hook.
In this repository the job is `public-repo-hygiene` in `.github/workflows/ci.yml` (a job in the existing workflow, because the pull-request-workflow ratchet admits no new workflow file).

The job reads no private vocabulary and uses no secret, so it runs on a fork pull
request. The caller pins the omniclaude commit that carries the job; the local hook runs the
same commit, so the local and CI verdicts cannot diverge.

Falsifier: drop the hook, or move it off the caller's revision, and the named test
fails.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CALLER = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PRECOMMIT = REPO_ROOT / ".pre-commit-config.yaml"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REUSABLE = "OmniNode-ai/omniclaude/.github/workflows/public-repo-hygiene-reusable.yml"
OMNICLAUDE = "https://github.com/OmniNode-ai/omniclaude"
CALLER_JOB_ID = "public-repo-hygiene"


def _load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path} did not parse to a mapping"
    return loaded


def _caller_pin() -> str:
    job = _load(CALLER)["jobs"][CALLER_JOB_ID]
    uses = str(job["uses"])
    assert uses.startswith(f"{REUSABLE}@"), uses
    return uses.removeprefix(f"{REUSABLE}@")


def test_caller_calls_the_reusable_hygiene_workflow_at_an_immutable_commit() -> None:
    pin = _caller_pin()
    assert SHA_RE.match(pin), f"pin must be a lowercase 40-hex commit, got {pin!r}"


def test_caller_job_runs_on_every_pull_request_to_dev() -> None:
    job = _load(CALLER)["jobs"][CALLER_JOB_ID]
    assert (
        job["if"] == "github.event_name == 'pull_request' && github.base_ref == 'dev'"
    )


def test_precommit_runs_the_deployment_config_hook_at_the_callers_revision() -> None:
    blocks = [
        (repo, hook)
        for repo in _load(PRECOMMIT)["repos"]
        if repo["repo"] == OMNICLAUDE
        for hook in repo.get("hooks", [])
        if hook.get("id") == "deployment-config"
    ]
    assert len(blocks) == 1, "exactly one deployment-config hook is declared"
    repo, hook = blocks[0]
    assert str(repo["rev"]).split()[0] == _caller_pin()
    # The exported hook already runs over the staged added lines, always_run, in the
    # pre-commit stage. An override here would narrow it.
    narrowing = {"entry", "args", "files", "exclude", "stages", "always_run"}
    assert not narrowing & set(hook), sorted(narrowing & set(hook))

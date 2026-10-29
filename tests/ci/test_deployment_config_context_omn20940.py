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
same hook set. Under the single-home invariant (OMN-21495) the caller and the
hook each own a distinct dev-merge tag of that repository, not one shared commit.

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

DEV_MERGE_TAG_RE = re.compile(r"^dev-[0-9]{14}-[0-9a-f]{12}$")
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


def test_caller_calls_the_reusable_hygiene_workflow_at_a_dev_merge_tag() -> None:
    pin = _caller_pin()
    assert DEV_MERGE_TAG_RE.match(pin), f"pin must be a dev-merge tag, got {pin!r}"


def test_caller_job_runs_on_every_pull_request_to_dev() -> None:
    job = _load(CALLER)["jobs"][CALLER_JOB_ID]
    assert (
        job["if"] == "github.event_name == 'pull_request' && github.base_ref == 'dev'"
    )


def test_precommit_runs_the_deployment_config_hook_at_a_dev_merge_tag() -> None:
    blocks = [
        (repo, hook)
        for repo in _load(PRECOMMIT)["repos"]
        if repo["repo"] == OMNICLAUDE
        for hook in repo.get("hooks", [])
        if hook.get("id") == "deployment-config"
    ]
    assert len(blocks) == 1, "exactly one deployment-config hook is declared"
    repo, hook = blocks[0]
    rev = str(repo["rev"]).split()[0]
    assert DEV_MERGE_TAG_RE.match(rev), f"hook rev must be a dev-merge tag, got {rev!r}"
    # The exported hook already runs over the staged added lines, always_run, in the
    # pre-commit stage. An override here would narrow it.
    narrowing = {"entry", "args", "files", "exclude", "stages", "always_run"}
    assert not narrowing & set(hook), sorted(narrowing & set(hook))

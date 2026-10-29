# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pin how the cross-repository dependency-direction check is wired (OMN-19998).

RULING 2026-10-15T21:52:44Z: "Market depends on infra, not the other way around."
The check is only a mechanism while a required CI job and a pre-commit hook both name
the handler module, so the audit that reads workflows and hooks can find it. A console
script alias is not a name the audit follows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"

HANDLER_MODULE = (
    "omnibase_core.nodes.node_dependency_direction_check_effect"
    ".runtime_dependency_direction_check"
)
STEP_NAME = "Run cross-repository dependency-direction check"
JOB_ID = "lint-imports"
HOOK_ID = "check-dependency-direction"


def _load(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path.name} must load as a mapping"
    return cast(dict[str, Any], loaded)


def _step_run(workflow: dict[str, Any]) -> str:
    steps = workflow["jobs"][JOB_ID]["steps"]
    for step in steps:
        if step.get("name") == STEP_NAME:
            return str(step["run"])
    raise AssertionError(f"{STEP_NAME!r} is not a step of job {JOB_ID}")


def _hook_entry(config: dict[str, Any]) -> str:
    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            if hook.get("id") == HOOK_ID:
                return str(hook["entry"])
    raise AssertionError(f"pre-commit hook {HOOK_ID} is not configured")


def test_ci_step_runs_the_handler_module() -> None:
    run = _step_run(_load(CI_WORKFLOW))
    assert f"python -m {HANDLER_MODULE}" in run


def test_ci_step_does_not_use_the_console_script_alias() -> None:
    run = _step_run(_load(CI_WORKFLOW))
    assert "uv run check-dependency-direction" not in run


def test_precommit_hook_runs_the_handler_module() -> None:
    assert HANDLER_MODULE in _hook_entry(_load(PRECOMMIT_CONFIG))


def test_negative_control_a_step_without_the_module_is_rejected() -> None:
    workflow: dict[str, Any] = {
        "jobs": {
            JOB_ID: {
                "steps": [
                    {
                        "name": STEP_NAME,
                        "run": "uv run check-dependency-direction --repo x",
                    }
                ]
            }
        }
    }
    assert f"python -m {HANDLER_MODULE}" not in _step_run(workflow)

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The omnimarket policy gate node is the step that reads the minted App token (OMN-20671)."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/handshake-policy-gate.yml"
NODE_MODULE = "omnimarket.nodes.node_handshake_policy_gate_effect"


def _steps() -> list[dict[str, object]]:
    document = yaml.safe_load(WORKFLOW.read_text())
    steps = document["jobs"]["policy-gate"]["steps"]
    assert isinstance(steps, list)
    return steps


def _active_repos() -> set[str]:
    lines = (REPO_ROOT / "architecture-handshakes/repos.conf").read_text().splitlines()
    return {
        line.split("#", 1)[0].strip() for line in lines if line.split("#", 1)[0].strip()
    }


def test_the_node_step_reads_the_token_the_mint_step_produced() -> None:
    steps = _steps()
    node_steps = [step for step in steps if NODE_MODULE in str(step.get("run", ""))]
    assert len(node_steps) == 1, "exactly one step must run the omnimarket node"
    node_step = node_steps[0]
    mint = next(
        step
        for step in steps
        if str(step.get("uses", "")).startswith("actions/create-github-app-token@")
    )
    assert steps.index(mint) < steps.index(node_step)
    env = node_step["env"]
    assert isinstance(env, dict)
    assert env["GH_TOKEN"] == f"${{{{ steps.{mint['id']}.outputs.token }}}}"


def test_the_token_covers_every_repository_the_node_is_told_to_read() -> None:
    steps = _steps()
    node_step = next(step for step in steps if NODE_MODULE in str(step.get("run", "")))
    assert "--repos-conf architecture-handshakes/repos.conf" in str(node_step["run"])
    mint = next(
        step
        for step in steps
        if str(step.get("uses", "")).startswith("actions/create-github-app-token@")
    )
    arguments = mint["with"]
    assert isinstance(arguments, dict)
    assert set(str(arguments["repositories"]).split()) == _active_repos()

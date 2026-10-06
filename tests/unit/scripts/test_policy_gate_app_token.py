# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Keep the policy gate's cross-repo credential scoped to its actual readers."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/handshake-policy-gate.yml"


def test_policy_gate_mints_token_for_every_active_repo() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["policy-gate"]["steps"]
    mint_steps = [
        step
        for step in steps
        if step.get("uses", "").startswith("actions/create-github-app-token@")
    ]
    assert len(mint_steps) == 1, "The gate must mint its cross-repo App token"
    mint = mint_steps[0]
    ci = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    ci_pins = {
        step["uses"]
        for job in ci["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith("actions/create-github-app-token@")
    }
    assert mint["uses"] in ci_pins
    assert mint["with"]["app-id"] == "${{ secrets.ONEXBOT_APP_ID }}"
    assert mint["with"]["private-key"] == "${{ secrets.ONEXBOT_APP_PRIVATE_KEY }}"
    assert mint["with"]["owner"] == "OmniNode-ai"
    active_repos = {
        line.split("#", 1)[0].strip()
        for line in (REPO_ROOT / "architecture-handshakes/repos.conf")
        .read_text()
        .splitlines()
        if line.split("#", 1)[0].strip()
    }
    assert set(mint["with"]["repositories"].split()) == active_repos
    gate = next(step for step in steps if step["name"] == "Run policy gate check")
    assert steps.index(mint) < steps.index(gate)
    assert gate["env"]["GH_TOKEN"] == f"${{{{ steps.{mint['id']}.outputs.token }}}}"
    assert "POLICY_GATE_TOKEN" not in WORKFLOW.read_text()

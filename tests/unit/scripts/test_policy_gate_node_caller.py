# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The handshake policy gate runs as omnimarket's node, and the retired shell script is gone."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/handshake-policy-gate.yml"
NODE_MODULE = "omnimarket.nodes.node_handshake_policy_gate_effect"
RETIRED_SCRIPT = "check-policy" + "-gate"


def _steps() -> list[dict[str, object]]:
    document = yaml.safe_load(WORKFLOW.read_text())
    assert isinstance(document, dict)
    steps = document["jobs"]["policy-gate"]["steps"]
    assert isinstance(steps, list)
    return steps


def _text(step: dict[str, object], key: str) -> str:
    value = step[key]
    assert isinstance(value, str)
    return value


def _with(step: dict[str, object]) -> dict[str, object]:
    value = step["with"]
    assert isinstance(value, dict)
    return value


def test_the_retired_script_and_its_tests_are_deleted() -> None:
    assert not (REPO_ROOT / "architecture-handshakes" / f"{RETIRED_SCRIPT}.sh").exists()
    assert not (
        REPO_ROOT / "tests/unit/scripts/test_check_policy_gate_retry.py"
    ).exists()


def test_no_tracked_file_still_names_the_retired_script() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env({"PATH": "/usr/bin:/bin:/usr/local/bin"}),
    ).stdout.splitlines()
    skipped = {"CHANGELOG.md"}
    callers = [
        name
        for name in tracked
        if name not in skipped
        and (REPO_ROOT / name).is_file()
        and RETIRED_SCRIPT.encode() in (REPO_ROOT / name).read_bytes()
    ]
    assert callers == []


def test_the_gate_step_runs_the_omnimarket_node_at_a_pinned_revision() -> None:
    steps = _steps()
    fetch = next(
        step
        for step in steps
        if _text(step, "name").startswith("Fetch the policy gate node")
    )
    assert _with(fetch)["repository"] == "OmniNode-ai/omnimarket"
    assert re.fullmatch(r"[0-9a-f]{40}", str(_with(fetch)["ref"]))
    assert _with(fetch)["persist-credentials"] is False
    gate = next(step for step in steps if step["name"] == "Run policy gate check")
    assert steps.index(fetch) < steps.index(gate)
    run = _text(gate, "run")
    assert f"python -m {NODE_MODULE}" in run
    assert "--repos-conf architecture-handshakes/repos.conf" in run
    assert '[ "${{ github.event_name }}" = "merge_group" ]' in run
    assert 'strict="--strict"' in run
    assert ".policy-gate-node-src" in run

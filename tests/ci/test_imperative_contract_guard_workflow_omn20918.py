# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20918: the reusable imperative contract guard workflow lives in omnibase_core.

It runs the guard from an omnibase_core checkout against the CALLER's tree and the
CALLER's own allowlist, named by a caller-relative path input, and refuses an
allowlist that gains a path against the merge base. It checks out no
onex_change_control repository, so a repository that repoints to it carries its
allowlist in its own tree and can widen nobody else's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "imperative-contract-guard.yml"
_FORBIDDEN_REFERENCE = "onex_change_control"
_CORE_REPOSITORY = "OmniNode-ai/omnibase_core"


def _load() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _triggers(data: dict[str, Any]) -> dict[str, Any]:
    # PyYAML 1.1 resolves the bare `on:` key to the boolean True.
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict), "workflow must declare a mapping on: block"
    return triggers


def _steps(data: dict[str, Any]) -> list[dict[str, Any]]:
    return data["jobs"]["imperative-contract-guard"]["steps"]


def _checkouts(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s
        for s in _steps(data)
        if str(s.get("uses", "")).startswith("actions/checkout@")
    ]


def _guard_step(data: dict[str, Any]) -> dict[str, Any]:
    (step,) = [
        s for s in _steps(data) if "check-imperative-contracts" in s.get("run", "")
    ]
    return step


def _references_occ(text: str) -> bool:
    return _FORBIDDEN_REFERENCE in text


def test_imperative_contract_guard_workflow_is_workflow_call_only() -> None:
    assert set(_triggers(_load())) == {"workflow_call"}


def test_imperative_contract_guard_workflow_checks_out_no_onex_change_control() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert not _references_occ(text)
    repositories = [c.get("with", {}).get("repository") for c in _checkouts(_load())]
    assert repositories == [None, _CORE_REPOSITORY]


def test_imperative_contract_guard_workflow_occ_reference_check_has_a_positive_control() -> (
    None
):
    mutated = WORKFLOW_PATH.read_text(encoding="utf-8").replace(
        _CORE_REPOSITORY, "OmniNode-ai/onex_change_control", 1
    )
    assert _references_occ(mutated)


def test_imperative_contract_guard_workflow_takes_a_caller_relative_allowlist_path() -> (
    None
):
    inputs = _triggers(_load())["workflow_call"]["inputs"]
    allowlist = inputs["allowlist-path"]
    assert allowlist["type"] == "string"
    assert allowlist["required"] is True
    assert "default" not in allowlist, "each caller must name its own allowlist"
    assert "relative to the caller" in " ".join(allowlist["description"].split())


def test_imperative_contract_guard_workflow_takes_the_ratchet_base_ref() -> None:
    inputs = _triggers(_load())["workflow_call"]["inputs"]
    base = inputs["ratchet-base-ref"]
    assert base["type"] == "string"
    assert base["required"] is False


def test_imperative_contract_guard_workflow_reads_the_allowlist_from_the_callers_tree() -> (
    None
):
    step = _guard_step(_load())
    env = step["env"]
    run = step["run"]
    assert env["ALLOWLIST_PATH"] == "${{ inputs['allowlist-path'] }}"
    assert '--repo-root "$GITHUB_WORKSPACE/target"' in run
    assert '--allowlist-path "$ALLOWLIST_PATH"' in run
    assert "--allowlists-dir" not in run, "no central allowlists directory"
    assert "allowlists/" not in run


def test_imperative_contract_guard_workflow_ratchets_against_the_pull_request_base() -> (
    None
):
    step = _guard_step(_load())
    base = " ".join(step["env"]["RATCHET_BASE_REF"].split())
    assert "inputs['ratchet-base-ref']" in base
    assert "github.event.pull_request.base.sha" in base
    assert '--ratchet-base-ref "$RATCHET_BASE_REF"' in step["run"]


def test_imperative_contract_guard_workflow_ratchet_needs_history_in_the_caller_checkout() -> (
    None
):
    target, _ = _checkouts(_load())
    assert target["with"]["path"] == "target"
    assert target["with"]["fetch-depth"] == 0


def test_imperative_contract_guard_workflow_runs_the_validator_from_the_core_checkout() -> (
    None
):
    data = _load()
    _, core = _checkouts(data)
    assert core["with"]["path"] == "omnibase_core"
    assert "github.job_workflow_sha" in core["with"]["ref"]
    step = _guard_step(data)
    assert step["working-directory"] == "omnibase_core"
    assert "uv run --no-sync check-imperative-contracts" in step["run"]


def test_imperative_contract_guard_workflow_keeps_the_job_name_and_least_privilege() -> (
    None
):
    data = _load()
    assert (
        data["jobs"]["imperative-contract-guard"]["name"] == "Imperative Contract Guard"
    )
    assert data["permissions"] == {"contents": "read"}


def test_imperative_contract_guard_workflow_cli_entry_point_is_declared() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (
        'check-imperative-contracts = "omnibase_core.handlers.'
        'handler_imperative_contract_guard_cli:main"'
    ) in pyproject

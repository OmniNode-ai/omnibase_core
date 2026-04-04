# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for RuntimeLocal handler loading and execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.runtime.runtime_local import RuntimeLocal, load_workflow_contract

VALID_WORKFLOW_YAML = (
    "workflow_id: test\n"
    "contract_version: {major: 1, minor: 0, patch: 0}\n"
    "node_type: workflow\n"
    "description: Test\n"
    "initial_command: cmd.test.v1\n"
    "terminal_event: evt.test.v1\n"
    "handler:\n"
    "  class: Foo\n"
    "  module: nonexistent.module\n"
    "nodes: []\n"
    "event_flow: []\n"
)


@pytest.mark.unit
def test_load_workflow_contract_valid(tmp_path: Path) -> None:
    """load_workflow_contract returns parsed dict for valid YAML."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(VALID_WORKFLOW_YAML)
    data = load_workflow_contract(workflow)
    assert data["workflow_id"] == "test"
    assert data["handler"]["class"] == "Foo"


@pytest.mark.unit
def test_runtime_local_fails_on_bad_handler(tmp_path: Path) -> None:
    """RuntimeLocal returns FAILED when handler module cannot be imported."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(VALID_WORKFLOW_YAML)
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=tmp_path / "state",
        timeout=5,
    )
    result = runtime.run()
    assert result == EnumWorkflowResult.FAILED


@pytest.mark.unit
def test_runtime_local_writes_state(tmp_path: Path) -> None:
    """RuntimeLocal writes workflow_result.json to state_root."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(VALID_WORKFLOW_YAML)
    state_dir = tmp_path / "state"
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=state_dir,
        timeout=5,
    )
    runtime.run()
    result_file = state_dir / "workflow_result.json"
    assert result_file.exists()
    import json

    data = json.loads(result_file.read_text())
    assert data["result"] == "failed"
    assert data["exit_code"] == 1


@pytest.mark.unit
def test_runtime_local_missing_handler_spec(tmp_path: Path) -> None:
    """RuntimeLocal returns FAILED when handler section is missing."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(
        "workflow_id: test\n"
        "contract_version: {major: 1, minor: 0, patch: 0}\n"
        "node_type: workflow\n"
        "description: Test\n"
        "initial_command: cmd.test.v1\n"
        "terminal_event: evt.test.v1\n"
        "nodes: []\n"
        "event_flow: []\n"
    )
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=tmp_path / "state",
        timeout=5,
    )
    result = runtime.run()
    assert result == EnumWorkflowResult.FAILED

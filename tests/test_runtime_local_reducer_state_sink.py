# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Test that RuntimeLocal persists reducer projections to ServiceStateDisk (OMN-8946).

Gating: persistence fires only when contract declares `node_type: reducer` AND
handler output is a dict with `"state"` key. State store layout per
service_state_disk.py:38-39 is `<state_root>/<node_id>/<scope_id>/state.yaml`.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.runtime.runtime_local import RuntimeLocal


def test_reducer_projection_persists_to_state_store(tmp_path: Path) -> None:
    """Reducer handler output is persisted via ProtocolStateStore.put()."""
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        "---\n"
        "name: proof_reducer\n"
        "node_type: reducer\n"
        "handler:\n"
        "  module: tests.fixtures.handler_proof_reducer\n"
        "  class: HandlerProofReducer\n"
        "  input_model: tests.fixtures.handler_proof_reducer.ModelProofReducerInput\n"
        "handler_routing:\n"
        "  default_handler: tests.fixtures.handler_proof_reducer:HandlerProofReducer\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"counter_delta": 7}), encoding="utf-8")

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        input_path=input_path,
        timeout=10,
    )
    result = runtime.run()

    assert result == EnumWorkflowResult.COMPLETED
    # Layout: <state_root>/<node_id>/<scope_id>/state.yaml
    # node_id derived from contract `name` with node_ prefix.
    state_yaml = tmp_path / "state" / "node_proof_reducer" / "default" / "state.yaml"
    assert state_yaml.exists(), f"state projection missing at {state_yaml}"
    envelope = yaml.safe_load(state_yaml.read_text(encoding="utf-8"))
    assert envelope["node_id"] == "node_proof_reducer"
    assert envelope["scope_id"] == "default"
    # ModelStateEnvelope field is `data`, not `state` (see model_state_envelope.py:28).
    assert envelope["data"]["counter"] == 7
    assert "written_at" in envelope


def test_non_reducer_contract_with_dict_state_does_not_persist(tmp_path: Path) -> None:
    """Dict-shape output from a non-reducer contract must NOT trigger persistence.

    Guards the 'accidental-dict-trigger' class of bugs the reviewer flagged.
    """
    contract_path = tmp_path / "contract.yaml"
    # Note: node_type is "compute", not "reducer".
    contract_path.write_text(
        "---\n"
        "name: proof_compute\n"
        "node_type: compute\n"
        "handler:\n"
        "  module: tests.fixtures.handler_proof_reducer\n"
        "  class: HandlerProofReducer\n"
        "  input_model: tests.fixtures.handler_proof_reducer.ModelProofReducerInput\n"
        "handler_routing:\n"
        "  default_handler: tests.fixtures.handler_proof_reducer:HandlerProofReducer\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"counter_delta": 7}), encoding="utf-8")

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        input_path=input_path,
        timeout=10,
    )
    runtime.run()

    # State dir may exist for workflow_result.json but no reducer projection.
    projection = tmp_path / "state" / "node_proof_compute" / "default" / "state.yaml"
    assert not projection.exists(), (
        "Non-reducer contract produced persisted state — authority gate failed"
    )

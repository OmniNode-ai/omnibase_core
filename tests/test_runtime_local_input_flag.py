# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Test that RuntimeLocal accepts an explicit input payload via file path (OMN-8938)."""

from __future__ import annotations

import json
from pathlib import Path

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.runtime.runtime_local import RuntimeLocal


def test_runtime_local_accepts_input_file(tmp_path: Path) -> None:
    """RuntimeLocal reads an input payload from disk when input_path is provided.

    Builds a minimal workflow contract pointing at the HandlerProofNoop fixture,
    writes a JSON payload to disk, invokes RuntimeLocal, and asserts the handler
    echoed the file's contents to state_root/echo.json — proving the full
    JSON file → model validation → handler invocation pipeline works.
    """
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        "---\n"
        "name: proof_noop\n"
        "node_type: compute\n"
        "terminal_event: onex.evt.proof.noop-completed.v1\n"
        "handler:\n"
        "  module: tests.fixtures.handler_proof_noop\n"
        "  class: HandlerProofNoop\n"
        "  input_model: tests.fixtures.handler_proof_noop.ModelProofNoopRequest\n"
        "handler_routing:\n"
        "  default_handler: tests.fixtures.handler_proof_noop:HandlerProofNoop\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "input.json"
    input_path.write_text(
        json.dumps({"name": "from-file", "count": 3}), encoding="utf-8"
    )

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        input_path=input_path,
        timeout=10,
    )
    result = runtime.run()

    assert result == EnumWorkflowResult.COMPLETED
    echo = json.loads((tmp_path / "state" / "echo.json").read_text(encoding="utf-8"))
    assert echo == {"name": "from-file", "count": 3}

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelContractMcpConfig (contract ``mcp:`` block, OMN-15920)."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_mcp_config import (
    ModelContractMcpConfig,
)
from omnibase_core.models.contracts.model_contract_mcp_tool import ModelContractMcpTool

_ENTRY: dict[str, object] = {
    "tool_name": "register_node",
    "description": "Register a new ONEX node with the cluster.",
    "timeout_seconds": 30,
    "input_model": "probe_pkg.models.ModelRegisterInput",
    "output_model": "probe_pkg.models.ModelRegisterOutput",
    "command_topic": "onex.cmd.probe-pkg.register-node.v1",
    "completed_topic": "onex.evt.probe-pkg.register-node-completed.v1",
    "failed_topic": "onex.evt.probe-pkg.register-node-failed.v1",
}
_VALID: dict[str, object] = {"expose": True, "tools": [_ENTRY]}


@pytest.mark.unit
class TestModelContractMcpConfig:
    def test_parses_expose_and_tools(self) -> None:
        cfg = ModelContractMcpConfig.model_validate(_VALID)
        assert cfg.expose is True
        assert isinstance(cfg.tools[0], ModelContractMcpTool)
        assert cfg.tools[0].tool_name == "register_node"

    def test_expose_is_required(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMcpConfig.model_validate({"tools": [_ENTRY]})
        assert any(e["loc"] == ("expose",) for e in exc_info.value.errors())

    def test_old_single_tool_block_is_refused(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMcpConfig.model_validate(
                {
                    "expose": True,
                    "tool_name": "register_node",
                    "description": "Register a node.",
                    "timeout_seconds": 30,
                }
            )
        assert any(e["type"] == "extra_forbidden" for e in exc_info.value.errors())

    def test_rejects_undeclared_key(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMcpConfig.model_validate({**_VALID, "retries": 3})
        assert any(e["type"] == "extra_forbidden" for e in exc_info.value.errors())

    def test_rejects_non_snake_case_tool_name(self) -> None:
        with pytest.raises(ValidationError):
            ModelContractMcpConfig.model_validate(
                {"expose": True, "tools": [{**_ENTRY, "tool_name": "Register-Node"}]}
            )

    def test_is_frozen(self) -> None:
        cfg = ModelContractMcpConfig.model_validate(_VALID)
        with pytest.raises(ValidationError):
            cfg.expose = False  # type: ignore[misc]

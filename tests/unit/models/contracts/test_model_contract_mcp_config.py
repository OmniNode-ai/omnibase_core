# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelContractMcpConfig (contract ``mcp:`` block, OMN-16451)."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_mcp_config import (
    ModelContractMcpConfig,
)

_VALID: dict[str, object] = {
    "expose": True,
    "tool_name": "register_node",
    "description": "Register a new ONEX node with the cluster.",
    "timeout_seconds": 30,
}


@pytest.mark.unit
class TestModelContractMcpConfig:
    def test_parses_the_four_consumed_keys(self) -> None:
        cfg = ModelContractMcpConfig.model_validate(_VALID)
        assert cfg.expose is True
        assert cfg.tool_name == "register_node"
        assert cfg.description.startswith("Register")
        assert cfg.timeout_seconds == 30

    @pytest.mark.parametrize("missing", sorted(_VALID))
    def test_every_field_is_required(self, missing: str) -> None:
        data = {k: v for k, v in _VALID.items() if k != missing}
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMcpConfig.model_validate(data)
        assert any(e["loc"] == (missing,) for e in exc_info.value.errors())

    def test_rejects_undeclared_key(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMcpConfig.model_validate({**_VALID, "retries": 3})
        assert any(e["type"] == "extra_forbidden" for e in exc_info.value.errors())

    def test_rejects_non_positive_timeout(self) -> None:
        with pytest.raises(ValidationError):
            ModelContractMcpConfig.model_validate({**_VALID, "timeout_seconds": 0})

    def test_rejects_non_snake_case_tool_name(self) -> None:
        with pytest.raises(ValidationError):
            ModelContractMcpConfig.model_validate(
                {**_VALID, "tool_name": "Register-Node"}
            )

    def test_is_frozen(self) -> None:
        cfg = ModelContractMcpConfig.model_validate(_VALID)
        with pytest.raises(ValidationError):
            cfg.expose = False  # type: ignore[misc]

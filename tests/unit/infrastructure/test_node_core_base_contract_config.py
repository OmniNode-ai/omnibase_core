# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for contract config resolution on NodeCoreBase (OMN-11430).

Proves that all nodes can access self.contract_config from their contract.yaml
at construction time as a typed model, without env var fallbacks.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_config import ModelContractConfig
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class _ConcreteNode(NodeCoreBase):
    """Minimal concrete node for testing."""

    async def process(self, input_data: Any) -> Any:
        return input_data


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.mark.unit
class TestNodeCoreBaseContractConfig:
    def test_contract_config_is_empty_model_when_no_contract(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        assert node.contract_config == ModelContractConfig()

    def test_contract_config_is_empty_model_when_contract_has_no_config_section(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        # contract_data without a config key
        object.__setattr__(
            node, "contract_data", {"name": "test_node", "node_type": "compute"}
        )
        assert node.contract_config == ModelContractConfig()

    def test_contract_config_returns_typed_config_from_dict_contract(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        object.__setattr__(
            node,
            "contract_data",
            {
                "name": "test_node",
                "node_type": "compute",
                "config": {"timeout_ms": 5000, "max_retries": 3},
            },
        )
        assert isinstance(node.contract_config, ModelContractConfig)
        assert node.contract_config.model_extra == {
            "timeout_ms": 5000,
            "max_retries": 3,
        }

    def test_contract_config_returns_typed_config_from_pydantic_model_contract(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        mock_contract = MagicMock()
        mock_contract.config = {"batch_size": 100, "dry_run": False}
        object.__setattr__(node, "contract_data", mock_contract)
        assert isinstance(node.contract_config, ModelContractConfig)
        assert node.contract_config.model_extra == {
            "batch_size": 100,
            "dry_run": False,
        }

    def test_contract_config_returns_empty_model_when_pydantic_model_has_no_config_attr(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        mock_contract = MagicMock(spec=[])  # spec=[] means no attributes
        object.__setattr__(node, "contract_data", mock_contract)
        assert node.contract_config == ModelContractConfig()

    def test_contract_config_returns_empty_model_when_contract_config_is_none(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        object.__setattr__(
            node,
            "contract_data",
            {"name": "test_node", "config": None},
        )
        assert node.contract_config == ModelContractConfig()

    def test_contract_config_rejects_non_mapping_config(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        object.__setattr__(
            node,
            "contract_data",
            {"name": "test_node", "config": "not-a-config-map"},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            _ = node.contract_config

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

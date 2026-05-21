# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for contract config resolution on NodeCoreBase (OMN-10815).

Proves that all nodes can access self.contract_config from their contract.yaml
at construction time, without env var fallbacks.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class _ConcreteNode(NodeCoreBase):
    """Minimal concrete node for testing."""

    async def process(self, input_data: Any) -> Any:
        return input_data


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.mark.unit
class TestNodeCoreBaseContractConfig:
    def test_contract_config_is_empty_dict_when_no_contract(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        assert node.contract_config == {}

    def test_contract_config_is_empty_dict_when_contract_has_no_config_section(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        # contract_data without a config key
        object.__setattr__(
            node, "contract_data", {"name": "test_node", "node_type": "compute"}
        )
        assert node.contract_config == {}

    def test_contract_config_returns_config_section_from_dict_contract(
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
        assert node.contract_config == {"timeout_ms": 5000, "max_retries": 3}

    def test_contract_config_returns_config_from_pydantic_model_contract(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        mock_contract = MagicMock()
        mock_contract.config = {"batch_size": 100, "dry_run": False}
        object.__setattr__(node, "contract_data", mock_contract)
        assert node.contract_config == {"batch_size": 100, "dry_run": False}

    def test_contract_config_returns_empty_dict_when_pydantic_model_has_no_config_attr(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        mock_contract = MagicMock(spec=[])  # spec=[] means no attributes
        object.__setattr__(node, "contract_data", mock_contract)
        assert node.contract_config == {}

    def test_contract_config_returns_empty_dict_when_contract_config_is_none(
        self, container: ModelONEXContainer
    ) -> None:
        node = _ConcreteNode(container)
        object.__setattr__(
            node,
            "contract_data",
            {"name": "test_node", "config": None},
        )
        assert node.contract_config == {}

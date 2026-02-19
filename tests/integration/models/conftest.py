# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for typed payload integration tests.

This module provides common fixtures used across the typed payload test modules:
- test_typed_payload_normalization.py
- test_typed_payload_backward_compat.py
- test_typed_payload_workflows.py

These fixtures enable consistent testing of typed payload models and union type
handling in node workflows.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelHttpIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_effect import NodeEffect

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60

# Version for test contracts
V1_0_0 = ModelSemVer(major=1, minor=0, patch=0)


class TestableNodeEffect(NodeEffect):
    """Test implementation of NodeEffect with injected subcontract."""

    def __init__(
        self,
        container: ModelONEXContainer,
        effect_subcontract: ModelEffectSubcontract,
    ) -> None:
        super().__init__(container)
        self.effect_subcontract = effect_subcontract


def create_test_effect_subcontract(
    *,
    name: str = "test_effect",
    operations: list[ModelEffectOperation] | None = None,
    retry_policy: ModelEffectRetryPolicy | None = None,
) -> ModelEffectSubcontract:
    """Factory to create effect subcontracts for testing."""
    if operations is None:
        operations = [
            ModelEffectOperation(
                operation_name="test_http_get",
                description="Test HTTP GET operation",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/data/${input.id}",
                    method="GET",
                    headers={"Accept": "application/json"},
                    timeout_ms=5000,
                ),
            ),
        ]

    if retry_policy is None:
        retry_policy = ModelEffectRetryPolicy(
            enabled=False,  # Disable retries for faster tests
        )

    return ModelEffectSubcontract(
        subcontract_name=name,
        version=V1_0_0,
        description=f"Test Effect: {name}",
        execution_mode="sequential_abort",
        operations=operations,
        default_retry_policy=retry_policy,
    )


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing."""
    container = MagicMock(spec=ModelONEXContainer)

    mock_http_handler = AsyncMock()
    mock_http_handler.execute = AsyncMock(
        return_value={"status": "success", "data": {"id": 123, "name": "test"}}
    )

    def get_service_side_effect(service_name: str) -> Any:
        if service_name == "ProtocolEffectHandler_HTTP":
            return mock_http_handler
        return MagicMock()

    container.get_service = MagicMock(side_effect=get_service_side_effect)
    return container


@pytest.fixture
def mock_http_handler(mock_container: ModelONEXContainer) -> AsyncMock:
    """Get the mock HTTP handler from the container."""
    return mock_container.get_service("ProtocolEffectHandler_HTTP")


@pytest.fixture
def effect_node(mock_container: ModelONEXContainer) -> NodeEffect:
    """Create a NodeEffect instance with a default subcontract."""
    effect_subcontract = create_test_effect_subcontract()
    return TestableNodeEffect(mock_container, effect_subcontract)

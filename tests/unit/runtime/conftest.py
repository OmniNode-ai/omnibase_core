"""
Shared fixtures for runtime test suite.

Provides reusable fixtures for:
- NodeInstance creation
- Mock runtime objects
- Sample envelopes and contracts
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer


class MockTestContract(ModelContractBase):
    """
    Minimal concrete contract class for testing NodeInstance.

    This is a concrete implementation of ModelContractBase that satisfies
    Pydantic validation while providing minimal required functionality
    for testing purposes.
    """

    def validate_node_specific_config(self) -> None:
        """No-op validation for tests - always passes."""


@pytest.fixture
def default_version() -> ModelSemVer:
    """Provide default SemVer version for tests."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def sample_envelope(default_version: ModelSemVer) -> ModelOnexEnvelope:
    """
    Create a sample ModelOnexEnvelope for testing.

    Provides a minimal valid envelope with sensible defaults
    for testing node instance handle() methods.
    """
    return ModelOnexEnvelope(
        envelope_id=uuid4(),
        envelope_version=default_version,
        correlation_id=uuid4(),
        source_node="test_source",
        operation="TEST_OPERATION",
        payload={"test_key": "test_value"},
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_envelope_with_target(default_version: ModelSemVer) -> ModelOnexEnvelope:
    """
    Create a sample envelope with target node specified.

    Used for testing routing and delegation patterns.
    """
    return ModelOnexEnvelope(
        envelope_id=uuid4(),
        envelope_version=default_version,
        correlation_id=uuid4(),
        source_node="test_source",
        target_node="test_target",
        operation="TARGETED_OPERATION",
        payload={"request": "data"},
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def mock_contract() -> MockTestContract:
    """
    Create a valid test contract for testing NodeInstance.

    Returns a concrete MockTestContract instance that satisfies
    Pydantic validation requirements while providing minimal
    required fields for testing.
    """
    return MockTestContract(
        name="test_contract",
        version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test contract for NodeInstance tests",
        node_type=EnumNodeType.COMPUTE_GENERIC,
        input_model="omnibase_core.models.test.TestInput",
        output_model="omnibase_core.models.test.TestOutput",
        dependencies=[],
        protocol_interfaces=[],
    )


@pytest.fixture
def mock_runtime() -> MagicMock:
    """
    Create a mock runtime for testing delegation patterns.

    Returns a MagicMock that can be used to verify:
    - execute_with_handler() calls
    - Envelope forwarding
    - Return value handling

    Note: execute_with_handler returns an awaitable to match the async protocol.
    """
    from unittest.mock import AsyncMock

    runtime = MagicMock()
    # Default return value for execute_with_handler (async method)
    runtime.execute_with_handler = AsyncMock(
        return_value={
            "status": "success",
            "result": {"processed": True},
        }
    )
    return runtime


@pytest.fixture
def mock_runtime_async() -> MagicMock:
    """
    Create a mock runtime with async method support.

    Used for testing async handle() patterns.
    """
    import asyncio

    runtime = MagicMock()

    async def mock_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "success", "result": {"processed": True}}

    runtime.execute_with_handler = Mock(side_effect=mock_execute)
    return runtime


@pytest.fixture
def sample_slug() -> str:
    """Provide a sample node slug for tests."""
    return "test-node-instance-slug"


@pytest.fixture
def sample_node_type() -> EnumNodeType:
    """Provide a sample node type for tests."""
    return EnumNodeType.COMPUTE_GENERIC

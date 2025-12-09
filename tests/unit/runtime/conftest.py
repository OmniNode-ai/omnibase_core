"""
Shared fixtures for runtime test suite.

This module provides reusable pytest fixtures for testing RuntimeNodeInstance
and related runtime components. All fixtures follow ONEX testing conventions.

Fixture Categories:
    - Model fixtures: default_version, sample_envelope, mock_contract
    - Mock fixtures: mock_runtime (async-aware runtime mock)
    - Identity fixtures: sample_slug, sample_node_type

Usage Pattern:
    Fixtures are auto-discovered by pytest. Use them as function parameters::

        def test_example(sample_slug, mock_contract, mock_runtime):
            instance = NodeInstance(slug=sample_slug, ...)
            instance.set_runtime(mock_runtime)

Note:
    The mock_runtime fixture uses AsyncMock for the execute_with_handler method,
    ensuring proper async/await behavior in tests. Always use set_runtime() to
    inject the mock, never assign to _runtime directly.

Related:
    - tests/unit/runtime/test_node_instance.py: Primary test consumers
    - src/omnibase_core/runtime/runtime_node_instance.py: Implementation
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock
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

    Note: For tests requiring specialized envelope configurations (e.g., with
    target_node for routing tests), create the envelope inline using this
    fixture as a template pattern. This avoids fixture proliferation while
    keeping test setup explicit and readable.
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

    Returns a MagicMock configured with AsyncMock for execute_with_handler(),
    which correctly handles async/await patterns in tests.

    Verifiable behaviors:
    - execute_with_handler() calls and arguments
    - Envelope forwarding to runtime
    - Return value handling

    Common verification patterns::

        # Verify method was called
        mock_runtime.execute_with_handler.assert_called_once()

        # Verify call arguments
        mock_runtime.execute_with_handler.assert_called_with(envelope, instance)

        # Get call arguments for detailed inspection
        call_args = mock_runtime.execute_with_handler.call_args
        passed_envelope = call_args.args[0]
        assert passed_envelope.envelope_id == expected_id

        # Reset for multiple test phases
        mock_runtime.execute_with_handler.reset_mock()

    Note: Uses AsyncMock which is the recommended approach for mocking
    async methods. AsyncMock automatically handles async/await properly,
    making it cleaner than manually defining async functions with side_effect.

    Important:
        Always use set_runtime() to inject this mock into NodeInstance:
            instance.set_runtime(mock_runtime)  # Correct
            instance._runtime = mock_runtime     # Avoid - bypasses validation
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
def sample_slug() -> str:
    """Provide a sample node slug for tests."""
    return "test-node-instance-slug"


@pytest.fixture
def sample_node_type() -> EnumNodeType:
    """Provide a sample node type for tests."""
    return EnumNodeType.COMPUTE_GENERIC

"""
Shared fixtures for runtime test suite.

This module provides reusable pytest fixtures for testing RuntimeNodeInstance,
NodeRuntime, and related runtime components. All fixtures follow ONEX testing
conventions.

Fixture Categories:
    - Model fixtures: default_version, sample_envelope, mock_contract
    - Mock fixtures: mock_runtime (async-aware runtime mock)
    - Handler fixtures: mock_handler, mock_handler_database, mock_handler_kafka
    - Identity fixtures: sample_slug, sample_node_type

Usage Pattern:
    Fixtures are auto-discovered by pytest. Use them as function parameters::

        def test_example(sample_slug, mock_contract, mock_runtime):
            instance = NodeInstance(slug=sample_slug, ...)
            instance.set_runtime(mock_runtime)

        def test_handler_example(mock_handler):
            runtime = NodeRuntime()
            runtime.register_handler(mock_handler)

Note:
    The mock_runtime fixture uses AsyncMock for the execute_with_handler method,
    ensuring proper async/await behavior in tests. Always use set_runtime() to
    inject the mock, never assign to _runtime directly.

    Handler fixtures (mock_handler, mock_handler_*) implement the handler protocol
    with AsyncMock for the execute method and appropriate handler_type.

Related:
    - tests/unit/runtime/test_node_instance.py: NodeInstance test consumers
    - tests/unit/runtime/test_node_runtime.py: NodeRuntime test consumers
    - src/omnibase_core/runtime/runtime_node_instance.py: RuntimeNodeInstance impl
    - src/omnibase_core/runtime/node_runtime.py: NodeRuntime implementation (TBD)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_handler_type import EnumHandlerType
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


# =============================================================================
# Handler Fixtures for NodeRuntime Tests (OMN-228)
# =============================================================================


def _create_mock_handler(
    handler_type: EnumHandlerType,
    *,
    success: bool = True,
    error_message: str | None = None,
) -> MagicMock:
    """
    Create a mock handler with the given handler_type.

    This internal helper creates handlers that implement the protocol:
    - handler_type property: Returns the EnumHandlerType
    - execute(envelope): Async method that processes envelopes
    - describe(): Returns handler metadata dict

    Args:
        handler_type: The handler type classification
        success: Whether execute() returns success (default True)
        error_message: Error message for failure cases (default None)

    Returns:
        MagicMock configured as a protocol-compliant handler
    """
    handler = MagicMock()
    handler.handler_type = handler_type

    # Create async execute method that returns a response envelope
    async def mock_execute(envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """Mock execute that returns a response envelope."""
        return ModelOnexEnvelope.create_response(
            request=envelope,
            payload={"handled": True, "handler_type": handler_type.value},
            success=success,
            error=error_message,
        )

    handler.execute = AsyncMock(side_effect=mock_execute)

    # Describe method for handler introspection (TypedDictHandlerMetadata)
    handler.describe.return_value = {
        "name": f"mock_{handler_type.value}_handler",
        "version": ModelSemVer(major=1, minor=0, patch=0),
        "description": f"Mock handler for {handler_type.value}",
        "capabilities": ["test", "mock"],
    }

    return handler


@pytest.fixture
def mock_handler() -> MagicMock:
    """
    Create a mock HTTP handler for testing NodeRuntime.

    Returns a MagicMock configured with:
    - handler_type property returning EnumHandlerType.HTTP
    - AsyncMock execute() that returns a success response envelope
    - describe() returning handler metadata

    Usage::

        def test_example(mock_handler):
            runtime = NodeRuntime()
            runtime.register_handler(mock_handler)

            # Verify handler was called
            mock_handler.execute.assert_called_once()

    Verifiable behaviors:
    - execute() calls and arguments
    - handler_type is HTTP
    - Returns success envelope by default
    """
    return _create_mock_handler(EnumHandlerType.HTTP)


@pytest.fixture
def mock_handler_alternate() -> MagicMock:
    """
    Create an alternate mock HTTP handler for replacement tests.

    Same as mock_handler but a different instance - useful for testing
    handler replacement behavior when registering a second handler
    with the same handler_type.
    """
    handler = _create_mock_handler(EnumHandlerType.HTTP)
    handler.describe.return_value["alternate"] = True
    return handler


@pytest.fixture
def mock_handler_database() -> MagicMock:
    """
    Create a mock DATABASE handler for testing multiple handler types.

    Returns a MagicMock configured with:
    - handler_type property returning EnumHandlerType.DATABASE
    - AsyncMock execute() that returns a success response envelope
    - describe() returning handler metadata
    """
    return _create_mock_handler(EnumHandlerType.DATABASE)


@pytest.fixture
def mock_handler_kafka() -> MagicMock:
    """
    Create a mock KAFKA handler for testing multiple handler types.

    Returns a MagicMock configured with:
    - handler_type property returning EnumHandlerType.KAFKA
    - AsyncMock execute() that returns a success response envelope
    - describe() returning handler metadata
    """
    return _create_mock_handler(EnumHandlerType.KAFKA)


@pytest.fixture
def mock_handler_with_error() -> MagicMock:
    """
    Create a mock handler that simulates execution errors.

    Returns a MagicMock configured to raise an exception when
    execute() is called. Used for testing error handling in
    NodeRuntime.execute_with_handler().

    The handler:
    - Has handler_type = HTTP
    - execute() raises RuntimeError("Handler execution failed")
    - describe() returns handler metadata

    Usage::

        @pytest.mark.asyncio
        async def test_error_handling(mock_handler_with_error):
            runtime = NodeRuntime()
            runtime.register_handler(mock_handler_with_error)

            result = await runtime.execute_with_handler(envelope, instance)
            assert result.success is False
            assert "error" in result.error.lower()
    """
    handler = MagicMock()
    handler.handler_type = EnumHandlerType.HTTP

    # Execute raises an error
    handler.execute = AsyncMock(side_effect=RuntimeError("Handler execution failed"))

    handler.describe.return_value = {
        "name": "mock_http_error_handler",
        "version": ModelSemVer(major=1, minor=0, patch=0),
        "description": "Mock handler that simulates execution errors",
        "capabilities": ["test", "error"],
        "error_mode": True,
    }

    return handler

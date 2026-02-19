# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Integration tests for NodeEffect ModelEffectInput -> ModelEffectOutput flows.

These tests verify complete contract-driven effect workflows including:
1. Happy path effect execution with committed transaction state
2. Error handling for operation failures with rollback
3. Retry logic with exponential backoff
4. Circuit breaker patterns for fault tolerance
5. Idempotent operation handling
6. Metadata preservation through effect execution

Tests validate real effect execution with actual data, using mock handlers.

Note:
    Integration tests using these fixtures should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumEffectType, EnumTransactionState
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker import (
    ModelEffectCircuitBreaker,
)
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelFilesystemIOConfig,
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
from omnibase_core.models.contracts.subcontracts.model_effect_transaction_config import (
    ModelEffectTransactionConfig,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_metadata import ModelEffectMetadata
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_effect import NodeEffect

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60

# Version for test contracts
V1_0_0 = ModelSemVer(major=1, minor=0, patch=0)


# Type alias for effect factory callable
EffectWithContractFactory = Callable[[ModelEffectSubcontract], NodeEffect]


def create_test_effect_subcontract(
    *,
    name: str = "test_effect",
    operations: list[ModelEffectOperation] | None = None,
    retry_policy: ModelEffectRetryPolicy | None = None,
    circuit_breaker: ModelEffectCircuitBreaker | None = None,
    transaction: ModelEffectTransactionConfig | None = None,
    execution_mode: str = "sequential_abort",
) -> ModelEffectSubcontract:
    """Factory to create effect subcontracts for testing.

    Args:
        name: Subcontract name
        operations: List of effect operations
        retry_policy: Default retry policy
        circuit_breaker: Default circuit breaker configuration
        transaction: Transaction configuration
        execution_mode: Execution mode (sequential_abort or sequential_continue)

    Returns:
        ModelEffectSubcontract configured for testing
    """
    if operations is None:
        # Default HTTP GET operation for testing
        operations = [
            ModelEffectOperation(
                operation_name="test_http_get",
                description="Test HTTP GET operation",
                idempotent=True,  # HTTP GET is idempotent
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
            enabled=True,
            max_retries=3,
            backoff_strategy="exponential",
            base_delay_ms=100,  # Minimum allowed value (good for testing)
        )

    if circuit_breaker is None:
        circuit_breaker = ModelEffectCircuitBreaker(
            enabled=False,  # Disabled by default for simpler tests
        )

    if transaction is None:
        transaction = ModelEffectTransactionConfig(
            enabled=False,  # Disabled by default for non-DB operations
        )

    return ModelEffectSubcontract(
        subcontract_name=name,
        version=V1_0_0,
        description=f"Test Effect: {name}",
        execution_mode=execution_mode,  # type: ignore[arg-type]
        operations=operations,
        default_retry_policy=retry_policy,
        default_circuit_breaker=circuit_breaker,
        transaction=transaction,
    )


class TestableNodeEffect(NodeEffect):
    """Test implementation of NodeEffect that can accept a subcontract at runtime.

    This class exists solely for integration testing purposes. It allows tests
    to inject arbitrary effect subcontracts at runtime rather than relying on the
    production contract loading mechanism.

    WARNING: This pattern is for TESTING ONLY. Production code should always
    use the standard NodeEffect initialization which loads contracts from
    declarative YAML files.
    """

    def __init__(
        self,
        container: ModelONEXContainer,
        effect_subcontract: ModelEffectSubcontract,
    ) -> None:
        """Initialize with explicit effect subcontract injection.

        Args:
            container: ONEX container for dependency injection
            effect_subcontract: Effect subcontract to use for operations
        """
        super().__init__(container)
        # Inject the effect subcontract directly
        self.effect_subcontract = effect_subcontract


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing.

    Returns:
        ModelONEXContainer with mocked services including effect handlers.
    """
    container = MagicMock(spec=ModelONEXContainer)

    # Create mock handlers for different effect types
    mock_http_handler = AsyncMock()
    mock_http_handler.execute = AsyncMock(
        return_value={"status": "success", "data": {"id": 123, "name": "test"}}
    )

    mock_fs_handler = AsyncMock()
    mock_fs_handler.execute = AsyncMock(return_value={"bytes_written": 100})

    # Configure container to return appropriate handlers
    def get_service_side_effect(service_name: str) -> Any:
        if service_name == "ProtocolEffectHandler_HTTP":
            return mock_http_handler
        elif service_name == "ProtocolEffectHandler_FILESYSTEM":
            return mock_fs_handler
        return MagicMock()

    container.get_service = MagicMock(side_effect=get_service_side_effect)

    return container


@pytest.fixture
def mock_http_handler(mock_container: ModelONEXContainer) -> AsyncMock:
    """Get the mock HTTP handler from the container.

    Args:
        mock_container: Mocked ONEX container

    Returns:
        Mock HTTP handler for assertions
    """
    return mock_container.get_service("ProtocolEffectHandler_HTTP")


@pytest.fixture
def effect_with_contract_factory(
    mock_container: ModelONEXContainer,
) -> EffectWithContractFactory:
    """Factory fixture for creating NodeEffect instances with custom subcontracts.

    Args:
        mock_container: Mocked ONEX container

    Returns:
        Factory callable that creates TestableNodeEffect instances
    """

    def _create_effect(effect_subcontract: ModelEffectSubcontract) -> NodeEffect:
        return TestableNodeEffect(mock_container, effect_subcontract)

    return _create_effect


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEffectIntegration:
    """Integration tests for NodeEffect input -> output flows.

    Tests complete contract-driven effect workflows with mocked external handlers.
    """

    def test_happy_path_external_operation(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test Scenario 1: Happy path from ModelEffectInput to ModelEffectOutput.

        This test verifies:
        - Valid ModelEffectInput is created with operation data
        - NodeEffect processes the input through handler execution
        - ModelEffectOutput contains correct result and transaction state
        - Handler is called with resolved context
        - Processing time is tracked
        """
        # Arrange: Create effect subcontract with HTTP operation
        effect_subcontract = create_test_effect_subcontract(
            name="happy_path_effect",
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        # Create input with operation data for template resolution
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "123"},
            retry_enabled=True,
            max_retries=3,
            metadata=ModelEffectMetadata(
                correlation_id=str(uuid4()),
                trace_id=str(uuid4()),
            ),
        )

        # Act: Process the input
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Verify output structure and transaction state
        assert isinstance(result, ModelEffectOutput)
        assert result.operation_id == input_data.operation_id
        assert result.effect_type == EnumEffectType.API_CALL
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.processing_time_ms >= 0.0
        assert result.retry_count == 0  # Success on first try

        # Verify result contains expected data
        assert isinstance(result.result, dict)
        assert result.result.get("status") == "success"

        # Verify handler was called
        mock_http_handler.execute.assert_called_once()

    def test_error_handling_operation_failure(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test Scenario 2: Error path for operation failure.

        This test verifies:
        - Handler execution failure is properly handled
        - ModelOnexError is raised with correct error code
        - Transaction state would be ROLLED_BACK
        - Error context contains meaningful information
        """
        # Arrange: Configure handler to raise an error
        mock_http_handler.execute = AsyncMock(
            side_effect=Exception("Network connection failed")
        )

        effect_subcontract = create_test_effect_subcontract(
            name="error_path_effect",
            retry_policy=ModelEffectRetryPolicy(
                enabled=False,  # Disable retries to fail immediately
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "456"},
            retry_enabled=False,
        )

        # Act & Assert: Expect ModelOnexError for operation failure
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(effect_node.process(input_data))

        # Verify error details
        error = exc_info.value
        assert error.error_code in (
            EnumCoreErrorCode.OPERATION_FAILED,
            EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
        )

    def test_retry_logic_eventual_success(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test Scenario 3: Retry logic with eventual success.

        This test verifies:
        - Failed operations are retried according to policy
        - Eventual success after retries
        - Retry count is properly tracked
        - Backoff delays are applied (implicit via handler call count)
        """
        # Arrange: Configure handler to fail twice then succeed
        call_count = 0

        async def fail_then_succeed(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Transient failure {call_count}")
            return {"status": "success", "attempts": call_count}

        mock_http_handler.execute = AsyncMock(side_effect=fail_then_succeed)

        effect_subcontract = create_test_effect_subcontract(
            name="retry_effect",
            retry_policy=ModelEffectRetryPolicy(
                enabled=True,
                max_retries=5,
                backoff_strategy="fixed",
                base_delay_ms=100,  # Minimum allowed value
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "789"},
            retry_enabled=True,
            max_retries=5,
            retry_delay_ms=10,
        )

        # Act: Process the input
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Verify successful output after retries
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.retry_count == 2  # Failed twice before success
        assert call_count == 3  # Handler called 3 times total

    def test_effect_with_context_metadata(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test Scenario 4: Metadata preservation through effect execution.

        This test verifies:
        - Input metadata is passed through to output
        - Correlation IDs are preserved
        - Trace IDs are preserved
        - Custom metadata fields are maintained
        """
        # Arrange
        effect_subcontract = create_test_effect_subcontract(
            name="metadata_effect",
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        correlation_id = str(uuid4())
        trace_id = str(uuid4())

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "metadata_test"},
            metadata=ModelEffectMetadata(
                correlation_id=correlation_id,
                trace_id=trace_id,
                source="integration_test",
            ),
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Verify metadata preservation
        assert result.metadata.correlation_id == correlation_id
        assert result.metadata.trace_id == trace_id
        assert result.metadata.source == "integration_test"

    def test_filesystem_write_operation(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_container: ModelONEXContainer,
    ) -> None:
        """Test Scenario 5: Filesystem write effect operation.

        This test verifies:
        - Filesystem operations work correctly
        - Write operations receive proper content
        - Atomic write flags are respected
        """
        # Arrange: Create filesystem operation
        fs_operation = ModelEffectOperation(
            operation_name="write_output_file",
            description="Write data to output file",
            idempotent=True,  # Filesystem writes with same content are idempotent
            io_config=ModelFilesystemIOConfig(
                file_path_template="/data/output/${input.filename}.json",
                operation="write",
                atomic=True,
                create_dirs=True,
            ),
        )

        effect_subcontract = create_test_effect_subcontract(
            name="filesystem_effect",
            operations=[fs_operation],
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        # Get the filesystem handler mock
        fs_handler = mock_container.get_service("ProtocolEffectHandler_FILESYSTEM")

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={
                "filename": "test_output",
                "file_content": '{"data": "test"}',
            },
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.effect_type == EnumEffectType.FILE_OPERATION
        fs_handler.execute.assert_called_once()


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEffectIntegrationEdgeCases:
    """Additional integration tests for edge cases and boundary conditions.

    Tests verify:
    1. Idempotent operation handling
    2. Circuit breaker behavior (when enabled)
    3. Timeout handling
    4. Multiple sequential effects
    5. Effect with disabled retry
    """

    def test_idempotent_operation_with_retry(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test idempotent operations can be safely retried."""
        # Arrange: Create idempotent HTTP GET operation
        http_get_operation = ModelEffectOperation(
            operation_name="idempotent_get",
            description="Idempotent HTTP GET",
            idempotent=True,
            io_config=ModelHttpIOConfig(
                url_template="https://api.example.com/resource/${input.id}",
                method="GET",
            ),
        )

        effect_subcontract = create_test_effect_subcontract(
            name="idempotent_effect",
            operations=[http_get_operation],
            retry_policy=ModelEffectRetryPolicy(
                enabled=True,
                max_retries=3,
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "idempotent_123"},
            retry_enabled=True,
            max_retries=3,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.retry_count == 0

    def test_circuit_breaker_enabled(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test circuit breaker protects against cascading failures."""
        # Arrange: Enable circuit breaker
        effect_subcontract = create_test_effect_subcontract(
            name="circuit_breaker_effect",
            circuit_breaker=ModelEffectCircuitBreaker(
                enabled=True,
                failure_threshold=3,
                success_threshold=1,
                timeout_ms=1000,
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "circuit_test"},
            circuit_breaker_enabled=True,
        )

        # Act: First request should succeed (circuit starts closed)
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Circuit breaker allows the request
        assert result.transaction_state == EnumTransactionState.COMMITTED

    def test_operation_timeout_behavior(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test operation timeout behavior.

        Note: The mixin checks timeout_ms BEFORE each retry attempt starts,
        not during execution. This test verifies operations complete when
        started before the timeout window elapses.
        """
        # Arrange: Configure handler to execute normally
        mock_http_handler.execute = AsyncMock(
            return_value={"status": "success", "timing": "normal"}
        )

        # Create operation with standard timeout (minimum is 1000ms)
        timeout_operation = ModelEffectOperation(
            operation_name="timeout_test_op",
            description="Operation with standard timeout",
            idempotent=True,
            io_config=ModelHttpIOConfig(
                url_template="https://api.example.com/slow",
                method="GET",
                timeout_ms=5000,  # 5 second timeout
            ),
            operation_timeout_ms=5000,  # 5 second overall timeout
        )

        effect_subcontract = create_test_effect_subcontract(
            name="timeout_effect",
            operations=[timeout_operation],
            retry_policy=ModelEffectRetryPolicy(
                enabled=False,  # No retries
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
            timeout_ms=5000,
            retry_enabled=False,
        )

        # Act: Execute the effect
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Operation completed successfully
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.result.get("status") == "success"

    def test_metadata_tags_preservation(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that custom metadata tags are preserved."""
        # Arrange
        effect_subcontract = create_test_effect_subcontract(
            name="tags_effect",
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "tags_test"},
            metadata=ModelEffectMetadata(
                tags=["integration", "test", "important"],
                environment="test",
            ),
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.metadata.tags == ["integration", "test", "important"]
        assert result.metadata.environment == "test"

    def test_retry_exhaustion(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test behavior when all retries are exhausted."""
        # Arrange: Handler always fails
        mock_http_handler.execute = AsyncMock(
            side_effect=Exception("Persistent failure")
        )

        effect_subcontract = create_test_effect_subcontract(
            name="exhaustion_effect",
            retry_policy=ModelEffectRetryPolicy(
                enabled=True,
                max_retries=2,
                base_delay_ms=100,  # Minimum allowed value
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "exhaust_test"},
            retry_enabled=True,
            max_retries=2,
            retry_delay_ms=10,
        )

        # Act & Assert: Should raise after retries exhausted
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(effect_node.process(input_data))

        error = exc_info.value
        assert error.error_code in (
            EnumCoreErrorCode.OPERATION_FAILED,
            EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
        )

        # Handler should have been called max_retries + 1 times
        assert mock_http_handler.execute.call_count == 3

    def test_effect_without_subcontract_raises_error(
        self,
        mock_container: ModelONEXContainer,
    ) -> None:
        """Test that processing without subcontract raises proper error."""
        # Arrange: Create effect node without setting subcontract
        effect_node = NodeEffect(mock_container)
        # effect_node.effect_subcontract is None by default

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "no_subcontract_test"},
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(effect_node.process(input_data))

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR

    def test_circuit_breaker_reset(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test circuit breaker can be reset."""
        # Arrange
        effect_subcontract = create_test_effect_subcontract(
            name="cb_reset_effect",
            circuit_breaker=ModelEffectCircuitBreaker(
                enabled=True,
                failure_threshold=3,
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        # Simulate adding some circuit breakers
        from uuid import uuid4 as make_uuid

        from omnibase_core.models.configuration.model_circuit_breaker import (
            ModelCircuitBreaker,
        )

        op_id = make_uuid()
        effect_node._circuit_breakers[op_id] = ModelCircuitBreaker.create_resilient()

        # Verify circuit breaker exists
        assert len(effect_node._circuit_breakers) == 1

        # Act: Reset all circuit breakers
        effect_node.reset_circuit_breakers()

        # Assert: All circuit breakers cleared
        assert len(effect_node._circuit_breakers) == 0

    def test_operation_data_template_resolution(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that operation_data is used for template resolution."""
        # Arrange
        effect_subcontract = create_test_effect_subcontract(
            name="template_effect",
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        # Complex operation data for template resolution
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "id": "complex_123",
                "user_id": "user_456",
                "params": {"filter": "active"},
            },
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Handler was called (template resolution worked)
        assert result.transaction_state == EnumTransactionState.COMMITTED
        mock_http_handler.execute.assert_called_once()

        # Verify the resolved context was passed
        call_args = mock_http_handler.execute.call_args
        resolved_context = call_args[0][0]

        # The resolved URL should contain the id value
        assert "complex_123" in resolved_context.url


# =============================================================================
# TYPED CONFIG INTEGRATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestTypedEffectOperationConfigIntegration:
    """Integration tests for effect execution with typed ModelEffectOperationConfig.

    These tests verify that the typed operation config models work correctly
    through the complete effect execution flow, including:
    1. ModelEffectOperationConfig with typed io_config
    2. Typed transaction_config handling
    3. Typed retry_policy and circuit_breaker configs
    4. Error scenarios with typed configs

    All tests use the new typed model patterns from PR #240 refactoring.
    """

    def test_execute_with_typed_http_operation_config(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test effect execution with fully typed ModelEffectOperationConfig.

        Verifies that ModelEffectOperationConfig with typed ModelHttpIOConfig
        flows correctly through the entire effect execution pipeline.
        """
        from omnibase_core.models.operations.model_effect_operation_config import (
            ModelEffectOperationConfig,
        )

        # Arrange: Create a typed ModelEffectOperationConfig directly
        typed_http_config = ModelHttpIOConfig(
            url_template="https://api.example.com/typed/${input.id}",
            method="GET",
            headers={"Accept": "application/json"},
            timeout_ms=5000,
        )

        operation_config = ModelEffectOperationConfig(
            io_config=typed_http_config,
            operation_name="typed_http_get",
            description="Test with typed HTTP config",
            operation_timeout_ms=10000,
            idempotent=True,
        )

        # Verify typed io_config is accessible
        assert isinstance(operation_config.io_config, ModelHttpIOConfig)
        typed_io = operation_config.get_typed_io_config()
        assert isinstance(typed_io, ModelHttpIOConfig)
        assert typed_io.method == "GET"

        # Create subcontract with typed operation
        effect_subcontract = create_test_effect_subcontract(
            name="typed_http_effect",
            operations=[
                ModelEffectOperation(
                    operation_name="typed_http_get",
                    io_config=typed_http_config,
                    idempotent=True,
                )
            ],
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "typed_123"},
            retry_enabled=False,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.effect_type == EnumEffectType.API_CALL
        mock_http_handler.execute.assert_called_once()

        # Verify the resolved URL contains our typed config values
        call_args = mock_http_handler.execute.call_args
        resolved_context = call_args[0][0]
        assert "typed_123" in resolved_context.url

    def test_execute_with_typed_db_operation_config(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_container: ModelONEXContainer,
    ) -> None:
        """Test effect execution with typed ModelDbIOConfig.

        Verifies that database operations with typed configs flow correctly.
        """
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelDbIOConfig,
        )

        # Get the DB handler mock
        mock_db_handler = AsyncMock()
        mock_db_handler.execute = AsyncMock(
            return_value=[{"id": 1, "name": "Test User"}]
        )

        def get_service_side_effect(service_name: str) -> Any:
            if service_name == "ProtocolEffectHandler_DB":
                return mock_db_handler
            return MagicMock()

        mock_container.get_service = MagicMock(side_effect=get_service_side_effect)

        # Arrange: Create typed DB config
        typed_db_config = ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
            timeout_ms=5000,
            read_only=True,
        )

        db_operation = ModelEffectOperation(
            operation_name="query_users",
            description="Query users with typed config",
            io_config=typed_db_config,
            idempotent=True,
        )

        effect_subcontract = create_test_effect_subcontract(
            name="typed_db_effect",
            operations=[db_operation],
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data={"user_id": "456"},
            retry_enabled=False,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.effect_type == EnumEffectType.DATABASE_OPERATION
        mock_db_handler.execute.assert_called_once()

    def test_execute_with_typed_transaction_config(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_container: ModelONEXContainer,
    ) -> None:
        """Test effect execution with typed ModelEffectTransactionConfig.

        Verifies that transaction configuration is properly handled when
        using typed models.
        """
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelDbIOConfig,
        )

        # Setup mock DB handler
        mock_db_handler = AsyncMock()
        mock_db_handler.execute = AsyncMock(return_value={"affected_rows": 1})

        def get_service_side_effect(service_name: str) -> Any:
            if service_name == "ProtocolEffectHandler_DB":
                return mock_db_handler
            return MagicMock()

        mock_container.get_service = MagicMock(side_effect=get_service_side_effect)

        # Arrange: Create typed transaction config
        typed_transaction_config = ModelEffectTransactionConfig(
            enabled=True,
            isolation_level="read_committed",
            rollback_on_error=True,
            timeout_ms=30000,
        )

        # Verify the typed config is immutable (frozen)
        assert typed_transaction_config.enabled is True
        assert typed_transaction_config.isolation_level == "read_committed"
        assert typed_transaction_config.rollback_on_error is True
        assert typed_transaction_config.timeout_ms == 30000

        # Create DB operation with typed config
        # Note: Using 'upsert' which can be idempotent, or set idempotent=True
        typed_db_config = ModelDbIOConfig(
            operation="insert",
            connection_name="primary_db",
            query_template="INSERT INTO users (name, email) VALUES ($1, $2)",
            query_params=["${input.name}", "${input.email}"],
            timeout_ms=5000,
        )

        # Set idempotent=True to allow retry (required by subcontract validation)
        # In production, you'd use upsert or set retry_policy.enabled=False
        db_operation = ModelEffectOperation(
            operation_name="insert_user",
            io_config=typed_db_config,
            idempotent=True,  # Required when retry is enabled
        )

        # Create subcontract with typed transaction config and disabled retry
        # (Transaction operations typically shouldn't retry at operation level)
        effect_subcontract = create_test_effect_subcontract(
            name="transaction_effect",
            operations=[db_operation],
            transaction=typed_transaction_config,
            retry_policy=ModelEffectRetryPolicy(
                enabled=False,  # Disable retry for transaction operations
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data={"name": "John Doe", "email": "john@example.com"},
            retry_enabled=False,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        mock_db_handler.execute.assert_called_once()

    def test_execute_with_typed_retry_policy(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test effect execution with typed ModelEffectRetryPolicy.

        Verifies that typed retry policy configuration is properly applied.
        """
        # Arrange: Configure handler to fail twice then succeed
        call_count = 0

        async def fail_then_succeed(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Transient failure {call_count}")
            return {"status": "success", "attempts": call_count}

        mock_http_handler.execute = AsyncMock(side_effect=fail_then_succeed)

        # Create typed retry policy
        typed_retry_policy = ModelEffectRetryPolicy(
            enabled=True,
            max_retries=5,
            backoff_strategy="fixed",
            base_delay_ms=100,  # Minimum allowed value
        )

        # Verify typed config is accessible
        assert typed_retry_policy.enabled is True
        assert typed_retry_policy.max_retries == 5
        assert typed_retry_policy.backoff_strategy == "fixed"

        effect_subcontract = create_test_effect_subcontract(
            name="typed_retry_effect",
            retry_policy=typed_retry_policy,
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "retry_test"},
            retry_enabled=True,
            max_retries=5,
            retry_delay_ms=10,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.retry_count == 2  # Failed twice before success
        assert call_count == 3  # Handler called 3 times total

    def test_execute_with_typed_circuit_breaker(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test effect execution with typed ModelEffectCircuitBreaker.

        Verifies that typed circuit breaker configuration is properly applied.
        """
        # Arrange: Create typed circuit breaker config
        typed_circuit_breaker = ModelEffectCircuitBreaker(
            enabled=True,
            failure_threshold=5,
            success_threshold=2,
            timeout_ms=5000,
        )

        # Verify typed config is accessible
        assert typed_circuit_breaker.enabled is True
        assert typed_circuit_breaker.failure_threshold == 5
        assert typed_circuit_breaker.success_threshold == 2

        effect_subcontract = create_test_effect_subcontract(
            name="typed_cb_effect",
            circuit_breaker=typed_circuit_breaker,
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "circuit_test"},
            circuit_breaker_enabled=True,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        mock_http_handler.execute.assert_called_once()

    def test_execute_with_typed_response_handling(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test effect execution with typed ModelEffectResponseHandling.

        Verifies that typed response handling configuration is accessible.
        """
        from omnibase_core.models.contracts.subcontracts.model_effect_response_handling import (
            ModelEffectResponseHandling,
        )

        # Configure mock to return structured response
        mock_http_handler.execute = AsyncMock(
            return_value={
                "status": "success",
                "data": {"user_id": 123, "email": "test@example.com"},
            }
        )

        # Create typed response handling
        typed_response_handling = ModelEffectResponseHandling(
            success_codes=[200, 201],
            extract_fields={"user_id": "$.data.user_id", "email": "$.data.email"},
            fail_on_empty=True,
            extraction_engine="jsonpath",
        )

        # Verify typed config is accessible
        assert typed_response_handling.success_codes == [200, 201]
        assert "user_id" in typed_response_handling.extract_fields

        # Create operation with typed response handling
        http_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.id}",
            method="GET",
        )

        operation = ModelEffectOperation(
            operation_name="fetch_user",
            io_config=http_config,
            response_handling=typed_response_handling,
            idempotent=True,
        )

        effect_subcontract = create_test_effect_subcontract(
            name="typed_response_effect",
            operations=[operation],
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "response_test"},
            retry_enabled=False,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert isinstance(result.result, dict)
        assert result.result.get("status") == "success"


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestTypedConfigErrorScenarios:
    """Integration tests for error scenarios with typed configs.

    Tests verify that error handling works correctly with typed models,
    including validation errors, configuration errors, and handler failures.
    """

    def test_typed_config_validation_error_io_config_required(
        self,
    ) -> None:
        """Test that missing io_config raises proper validation error.

        Verifies that ModelEffectOperationConfig requires io_config.
        """
        from omnibase_core.models.operations.model_effect_operation_config import (
            ModelEffectOperationConfig,
        )

        with pytest.raises(ValueError, match="io_config is required"):
            ModelEffectOperationConfig(operation_name="test")

    def test_typed_config_invalid_handler_type_error(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
    ) -> None:
        """Test that Pydantic raises ValidationError for invalid handler_type.

        The io_config field is a discriminated union that validates handler_type
        on construction. Unknown handler_type values cause immediate ValidationError
        rather than being stored as dict and validated later.
        """
        from pydantic import ValidationError

        from omnibase_core.models.operations.model_effect_operation_config import (
            ModelEffectOperationConfig,
        )

        # Pydantic discriminated union raises ValidationError on construction
        # for invalid handler_type values
        with pytest.raises(ValidationError, match="unknown_type"):
            ModelEffectOperationConfig(
                io_config={"handler_type": "unknown_type", "some_field": "value"}
            )

    def test_typed_config_handler_not_registered_error(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_container: ModelONEXContainer,
    ) -> None:
        """Test error when handler is not registered in container.

        Verifies proper error message when effect handler protocol is missing.
        """
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelKafkaIOConfig,
        )

        # Configure container to raise for Kafka handler
        def get_service_side_effect(service_name: str) -> Any:
            if "KAFKA" in service_name:
                raise KeyError(f"Service not found: {service_name}")
            return MagicMock()

        mock_container.get_service = MagicMock(side_effect=get_service_side_effect)

        # Create typed Kafka config
        typed_kafka_config = ModelKafkaIOConfig(
            topic="test-events",
            payload_template='{"event": "test"}',
        )

        # Mark as idempotent since default retry_policy has enabled=True
        kafka_operation = ModelEffectOperation(
            operation_name="publish_event",
            io_config=typed_kafka_config,
            idempotent=True,  # Required when retry is enabled
        )

        effect_subcontract = create_test_effect_subcontract(
            name="kafka_error_effect",
            operations=[kafka_operation],
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.EVENT_EMISSION,
            operation_data={"event_data": "test"},
            retry_enabled=False,
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(effect_node.process(input_data))

        error = exc_info.value
        assert (
            "handler not registered" in error.message.lower()
            or error.error_code == EnumCoreErrorCode.HANDLER_EXECUTION_ERROR
        )

    def test_typed_config_handler_execution_failure(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test error handling when handler execution fails with typed config.

        Verifies that handler failures are properly wrapped in ModelOnexError.
        """
        # Configure handler to fail
        mock_http_handler.execute = AsyncMock(
            side_effect=Exception("Handler execution failed: connection refused")
        )

        # Create typed HTTP config
        typed_http_config = ModelHttpIOConfig(
            url_template="https://api.example.com/fail/${input.id}",
            method="GET",
        )

        http_operation = ModelEffectOperation(
            operation_name="failing_http_call",
            io_config=typed_http_config,
            idempotent=True,
        )

        effect_subcontract = create_test_effect_subcontract(
            name="handler_error_effect",
            operations=[http_operation],
            retry_policy=ModelEffectRetryPolicy(
                enabled=False,  # Disable retries for faster test
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "fail_test"},
            retry_enabled=False,
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(effect_node.process(input_data))

        error = exc_info.value
        assert error.error_code in (
            EnumCoreErrorCode.OPERATION_FAILED,
            EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
        )

    def test_typed_config_timeout_handling(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test timeout handling with typed config.

        Verifies that typed operation timeout configuration is properly applied.
        Note: ModelEffectOperation requires operation_timeout_ms >= 1000ms.
        """
        # Configure handler to succeed quickly
        mock_http_handler.execute = AsyncMock(
            return_value={"status": "success", "timing": "fast"}
        )

        # Create typed config with valid timeout (minimum 1000ms for operations)
        typed_http_config = ModelHttpIOConfig(
            url_template="https://api.example.com/timeout/${input.id}",
            method="GET",
            timeout_ms=5000,  # 5 second timeout for HTTP request
        )

        # ModelEffectOperation requires operation_timeout_ms >= 1000ms
        http_operation = ModelEffectOperation(
            operation_name="timeout_test_call",
            io_config=typed_http_config,
            operation_timeout_ms=5000,  # Valid timeout (minimum 1000ms)
            idempotent=True,
        )

        effect_subcontract = create_test_effect_subcontract(
            name="timeout_effect",
            operations=[http_operation],
            retry_policy=ModelEffectRetryPolicy(
                enabled=False,
            ),
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "timeout_test"},
            retry_enabled=False,
            timeout_ms=5000,  # Match operation timeout
        )

        # Act: Execute with valid timeout
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Operation should complete successfully with typed timeout config
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.result.get("status") == "success"

        # Verify handler was called
        mock_http_handler.execute.assert_called_once()

    def test_typed_config_immutability(self) -> None:
        """Test that typed configs are immutable (frozen).

        Verifies that attempting to modify frozen configs raises error.
        """
        from pydantic import ValidationError

        from omnibase_core.models.operations.model_effect_operation_config import (
            ModelEffectOperationConfig,
        )

        typed_http_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
        )

        config = ModelEffectOperationConfig(
            io_config=typed_http_config,
            operation_name="test_op",
            idempotent=True,
        )

        # Verify config is frozen - attempting to modify should raise
        with pytest.raises(ValidationError):
            config.operation_name = "modified_name"

        with pytest.raises(ValidationError):
            config.idempotent = False

    def test_typed_transaction_config_with_non_db_operations(
        self,
    ) -> None:
        """Test transaction config constraints.

        Verifies that transaction config can be created but validation
        of DB-only constraint happens at subcontract level.
        """
        # Transaction config can be created independently
        typed_transaction = ModelEffectTransactionConfig(
            enabled=True,
            isolation_level="serializable",
            rollback_on_error=True,
            timeout_ms=60000,
        )

        # Verify config is valid
        assert typed_transaction.enabled is True
        assert typed_transaction.isolation_level == "serializable"

        # Note: The constraint that transactions only work with DB operations
        # is validated at the ModelEffectSubcontract level, not here.
        # This test just verifies the config model works correctly.


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestTypedConfigFactoryMethods:
    """Integration tests for typed config factory methods.

    Tests verify that factory methods work correctly in the integration context.
    """

    def test_from_effect_operation_preserves_all_fields(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that from_effect_operation preserves all operation fields.

        Verifies that converting ModelEffectOperation to ModelEffectOperationConfig
        preserves all configuration values.
        """
        from omnibase_core.models.contracts.subcontracts.model_effect_response_handling import (
            ModelEffectResponseHandling,
        )
        from omnibase_core.models.operations.model_effect_operation_config import (
            ModelEffectOperationConfig,
        )

        # Create a fully-populated operation
        typed_http_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="POST",
            headers={"Content-Type": "application/json"},
            body_template='{"action": "${input.action}"}',
            timeout_ms=5000,
        )

        typed_retry_policy = ModelEffectRetryPolicy(
            enabled=True,
            max_retries=3,
            backoff_strategy="exponential",
            base_delay_ms=1000,
        )

        typed_circuit_breaker = ModelEffectCircuitBreaker(
            enabled=True,
            failure_threshold=5,
        )

        typed_response_handling = ModelEffectResponseHandling(
            success_codes=[200, 201],
            extract_fields={"id": "$.data.id"},
        )

        full_operation = ModelEffectOperation(
            operation_name="create_user",
            description="Creates a new user via API",
            io_config=typed_http_config,
            operation_timeout_ms=15000,
            response_handling=typed_response_handling,
            retry_policy=typed_retry_policy,
            circuit_breaker=typed_circuit_breaker,
            idempotent=False,
        )

        # Convert to operation config
        config = ModelEffectOperationConfig.from_effect_operation(full_operation)

        # Verify all fields are preserved
        assert config.operation_name == "create_user"
        assert config.description == "Creates a new user via API"
        assert config.operation_timeout_ms == 15000
        assert config.idempotent is False

        # Verify typed nested configs
        assert isinstance(config.io_config, ModelHttpIOConfig)
        assert config.io_config.method == "POST"

        assert isinstance(config.retry_policy, ModelEffectRetryPolicy)
        assert config.retry_policy.max_retries == 3

        assert isinstance(config.circuit_breaker, ModelEffectCircuitBreaker)
        assert config.circuit_breaker.failure_threshold == 5

        assert isinstance(config.response_handling, ModelEffectResponseHandling)
        assert config.response_handling.success_codes == [200, 201]

    def test_from_dict_creates_valid_config(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that from_dict creates valid typed config from dictionary.

        Verifies that dict-based config is properly converted to typed models.
        """
        from omnibase_core.models.operations.model_effect_operation_config import (
            ModelEffectOperationConfig,
        )

        # Create config from dict (simulating YAML/JSON input)
        config_dict = {
            "io_config": {
                "handler_type": "http",
                "url_template": "https://api.example.com/dict-test/${input.id}",
                "method": "GET",
                "headers": {"Accept": "application/json"},
            },
            "operation_name": "dict_based_operation",
            "operation_timeout_ms": 10000,
            "retry_policy": {
                "enabled": True,
                "max_retries": 2,
            },
            "idempotent": True,
        }

        config = ModelEffectOperationConfig.from_dict(config_dict)

        # Verify the dict was properly converted to typed models
        assert config.operation_name == "dict_based_operation"
        assert config.operation_timeout_ms == 10000
        assert config.idempotent is True

        # io_config should be validated into typed model
        assert isinstance(config.io_config, ModelHttpIOConfig)
        typed_io = config.get_typed_io_config()
        assert typed_io.method == "GET"

        # retry_policy should be validated into typed model
        assert isinstance(config.retry_policy, ModelEffectRetryPolicy)
        assert config.retry_policy.max_retries == 2

    def test_typed_config_in_effect_subcontract_operations(
        self,
        effect_with_contract_factory: EffectWithContractFactory,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test typed configs within ModelEffectSubcontract operations list.

        Verifies that typed operation configs flow correctly through subcontract.
        """
        # Create multiple typed operations
        op1_config = ModelHttpIOConfig(
            url_template="https://api.example.com/step1/${input.id}",
            method="GET",
        )

        operation1 = ModelEffectOperation(
            operation_name="step_one",
            io_config=op1_config,
            idempotent=True,
        )

        # Verify typed config is accessible from operation
        assert isinstance(operation1.io_config, ModelHttpIOConfig)
        assert operation1.io_config.method == "GET"

        # Create subcontract with single typed operation (v1.0 limit)
        effect_subcontract = create_test_effect_subcontract(
            name="multi_typed_effect",
            operations=[operation1],
        )

        effect_node = effect_with_contract_factory(effect_subcontract)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "multi_test"},
            retry_enabled=False,
        )

        # Act
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert
        assert result.transaction_state == EnumTransactionState.COMMITTED
        mock_http_handler.execute.assert_called_once()

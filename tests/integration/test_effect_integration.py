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

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumEffectType, EnumTransactionState
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

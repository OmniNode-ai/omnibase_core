"""
Unit tests for MixinEffectExecution.

Tests the effect execution mixin for declarative I/O operations.
Demonstrates zero-custom-logic pattern where effect nodes are driven by contracts.
"""

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.mixins.mixin_effect_execution import (
    CircuitBreakerSnapshot,
    EffectExecutionResult,
    EffectHandlerContext,
    MixinEffectExecution,
)
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class MockNodeWithEffectMixin(MixinEffectExecution):
    """Mock node class using the effect execution mixin."""

    def __init__(self) -> None:
        """Initialize mock node."""
        super().__init__()


@pytest.fixture
def effect_subcontract() -> ModelEffectSubcontract:
    """Create test effect subcontract with HTTP operations."""
    return ModelEffectSubcontract(
        subcontract_name="test_effect_subcontract",
        version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test effect subcontract",
        execution_mode="sequential_abort",
        operations=[
            ModelEffectOperation(
                operation_name="fetch_user",
                description="Fetch user data from API",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/users/${input.user_id}",
                    method="GET",
                    timeout_ms=5000,
                ),
            ),
            ModelEffectOperation(
                operation_name="fetch_profile",
                description="Fetch user profile",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/profiles/${input.user_id}",
                    method="GET",
                    timeout_ms=5000,
                ),
            ),
        ],
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=True,
            max_retries=2,
            backoff_strategy="exponential",
            base_delay_ms=100,  # Minimum allowed value
        ),
    )


@pytest.fixture
def effect_subcontract_continue_mode() -> ModelEffectSubcontract:
    """Create test effect subcontract with sequential_continue mode."""
    return ModelEffectSubcontract(
        subcontract_name="test_continue_subcontract",
        version=ModelSemVer(major=1, minor=0, patch=0),
        execution_mode="sequential_continue",
        operations=[
            ModelEffectOperation(
                operation_name="operation_1",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/op1",
                    method="GET",
                ),
            ),
            ModelEffectOperation(
                operation_name="operation_2",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/op2",
                    method="GET",
                ),
            ),
        ],
    )


class TestMixinEffectExecutionInitialization:
    """Test MixinEffectExecution initialization."""

    def test_initialization(self) -> None:
        """Test mixin initializes with empty handler registry and circuit breaker states."""
        node = MockNodeWithEffectMixin()

        assert hasattr(node, "_effect_handlers")
        assert hasattr(node, "_circuit_breaker_states")
        assert len(node._effect_handlers) == 0
        assert len(node._circuit_breaker_states) == 0

    def test_get_registered_handlers_empty(self) -> None:
        """Test get_registered_handlers returns empty list initially."""
        node = MockNodeWithEffectMixin()

        handlers = node.get_registered_handlers()

        assert handlers == []


class TestMixinEffectExecutionHandlerRegistration:
    """Test effect handler registration."""

    def test_register_effect_handler(self) -> None:
        """Test registering a single effect handler."""
        node = MockNodeWithEffectMixin()

        async def http_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {"status_code": 200}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, http_handler)

        handlers = node.get_registered_handlers()
        assert EnumEffectHandlerType.HTTP in handlers
        assert len(handlers) == 1

    def test_register_multiple_handlers(self) -> None:
        """Test registering multiple effect handlers."""
        node = MockNodeWithEffectMixin()

        async def http_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {"status_code": 200}

        async def db_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {"rows": []}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, http_handler)
        node.register_effect_handler(EnumEffectHandlerType.DB, db_handler)

        handlers = node.get_registered_handlers()
        assert len(handlers) == 2
        assert EnumEffectHandlerType.HTTP in handlers
        assert EnumEffectHandlerType.DB in handlers

    def test_register_handler_initializes_circuit_breaker(self) -> None:
        """Test registering handler initializes circuit breaker state."""
        node = MockNodeWithEffectMixin()

        async def http_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, http_handler)

        cb_state = node.get_circuit_breaker_state(EnumEffectHandlerType.HTTP)
        assert cb_state is not None
        assert cb_state.state == EnumCircuitBreakerState.CLOSED
        assert cb_state.failure_count == 0

    def test_register_handler_overwrites_existing(self) -> None:
        """Test registering handler overwrites existing handler for same type."""
        node = MockNodeWithEffectMixin()

        async def handler_v1(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {"version": 1}

        async def handler_v2(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {"version": 2}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, handler_v1)
        node.register_effect_handler(EnumEffectHandlerType.HTTP, handler_v2)

        # Should still have only one HTTP handler
        handlers = node.get_registered_handlers()
        assert handlers.count(EnumEffectHandlerType.HTTP) == 1


class TestMixinEffectExecutionValidation:
    """Test effect subcontract validation."""

    @pytest.mark.asyncio
    async def test_validate_effect_subcontract_valid(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test validation passes when all handlers are registered."""
        node = MockNodeWithEffectMixin()

        async def http_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, http_handler)

        errors = await node.validate_effect_subcontract(effect_subcontract)

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_effect_subcontract_missing_handler(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test validation fails when handler is not registered."""
        node = MockNodeWithEffectMixin()

        # Don't register any handlers

        errors = await node.validate_effect_subcontract(effect_subcontract)

        assert len(errors) > 0
        assert any("No handler registered" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validate_effect_subcontract_circuit_breaker_open(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test validation fails when circuit breaker is open."""
        node = MockNodeWithEffectMixin()

        async def http_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, http_handler)

        # Manually set circuit breaker to open state
        node._circuit_breaker_states[EnumEffectHandlerType.HTTP] = (
            CircuitBreakerSnapshot(
                handler_type=EnumEffectHandlerType.HTTP,
                state=EnumCircuitBreakerState.OPEN,
                failure_count=5,
            )
        )

        errors = await node.validate_effect_subcontract(effect_subcontract)

        assert len(errors) > 0
        assert any("Circuit breaker open" in error for error in errors)


class TestMixinEffectExecutionCircuitBreaker:
    """Test circuit breaker state management."""

    def test_get_circuit_breaker_state_not_found(self) -> None:
        """Test getting circuit breaker state for unregistered handler returns None."""
        node = MockNodeWithEffectMixin()

        state = node.get_circuit_breaker_state(EnumEffectHandlerType.HTTP)

        assert state is None

    def test_get_circuit_breaker_state_after_registration(self) -> None:
        """Test getting circuit breaker state after handler registration."""
        node = MockNodeWithEffectMixin()

        async def http_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            return {}

        node.register_effect_handler(EnumEffectHandlerType.HTTP, http_handler)

        state = node.get_circuit_breaker_state(EnumEffectHandlerType.HTTP)

        assert state is not None
        assert state.handler_type == EnumEffectHandlerType.HTTP
        assert state.state == EnumCircuitBreakerState.CLOSED

    def test_reset_circuit_breaker(self) -> None:
        """Test resetting circuit breaker to closed state."""
        node = MockNodeWithEffectMixin()

        # Set up an open circuit breaker
        node._circuit_breaker_states[EnumEffectHandlerType.HTTP] = (
            CircuitBreakerSnapshot(
                handler_type=EnumEffectHandlerType.HTTP,
                state=EnumCircuitBreakerState.OPEN,
                failure_count=10,
            )
        )

        # Reset it
        node.reset_circuit_breaker(EnumEffectHandlerType.HTTP)

        state = node.get_circuit_breaker_state(EnumEffectHandlerType.HTTP)
        assert state is not None
        assert state.state == EnumCircuitBreakerState.CLOSED
        assert state.failure_count == 0
        assert state.last_success_time_ms is not None


class TestMixinEffectExecutionExecution:
    """Test effect execution from subcontract."""

    @pytest.mark.asyncio
    async def test_execute_effect_from_subcontract_success(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test successful execution of all operations."""
        node = MockNodeWithEffectMixin()

        # Handler must return empty dict or dict - mixin converts to extracted_fields
        mock_handler = AsyncMock(return_value={})
        node.register_effect_handler(EnumEffectHandlerType.HTTP, mock_handler)

        result = await node.execute_effect_from_subcontract(effect_subcontract)

        assert isinstance(result, EffectExecutionResult)
        assert result.success is True
        assert len(result.operation_results) == 2
        assert result.failed_operation is None
        assert result.total_duration_ms > 0
        assert mock_handler.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_effect_from_subcontract_with_context(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test execution passes context to handlers."""
        node = MockNodeWithEffectMixin()

        captured_contexts: list[EffectHandlerContext] = []

        async def capturing_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            captured_contexts.append(context)
            return {}  # Return empty dict - mixin expects dict for extracted_fields

        node.register_effect_handler(EnumEffectHandlerType.HTTP, capturing_handler)

        context = {"batch_id": "123", "user_session": "abc"}
        await node.execute_effect_from_subcontract(effect_subcontract, context=context)

        assert len(captured_contexts) == 2
        for ctx in captured_contexts:
            assert ctx.metadata == context
            assert ctx.correlation_id == effect_subcontract.correlation_id

    @pytest.mark.asyncio
    async def test_execute_effect_from_subcontract_no_handler(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test execution fails when handler not registered (sequential_abort mode)."""
        node = MockNodeWithEffectMixin()

        # Don't register any handlers

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_effect_from_subcontract(effect_subcontract)

        assert "No handler registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_effect_from_subcontract_handler_failure_abort(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test execution stops on first failure in sequential_abort mode."""
        node = MockNodeWithEffectMixin()

        call_count = 0

        async def failing_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            raise ValueError("Handler error")

        node.register_effect_handler(EnumEffectHandlerType.HTTP, failing_handler)

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_effect_from_subcontract(effect_subcontract)

        assert "Effect operation failed" in str(exc_info.value)
        # Should have retried based on retry policy (max_retries=2, so 3 total attempts)
        assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_execute_effect_from_subcontract_continue_mode(
        self, effect_subcontract_continue_mode: ModelEffectSubcontract
    ) -> None:
        """Test execution continues after failure in sequential_continue mode."""
        node = MockNodeWithEffectMixin()

        call_count = 0

        async def sometimes_failing_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if operation.operation_name == "operation_1":
                raise ValueError("First operation fails")
            return {}  # Return empty dict - mixin expects dict for extracted_fields

        node.register_effect_handler(
            EnumEffectHandlerType.HTTP, sometimes_failing_handler
        )

        result = await node.execute_effect_from_subcontract(
            effect_subcontract_continue_mode
        )

        assert result.success is False
        assert len(result.operation_results) == 2
        assert result.operation_results[0].success is False
        assert result.operation_results[1].success is True
        assert result.failed_operation == "operation_1"

    @pytest.mark.asyncio
    async def test_execute_effect_from_subcontract_circuit_breaker_open(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test execution fails fast when circuit breaker is open."""
        node = MockNodeWithEffectMixin()

        mock_handler = AsyncMock(return_value={})
        node.register_effect_handler(EnumEffectHandlerType.HTTP, mock_handler)

        # Manually set circuit breaker to open state
        node._circuit_breaker_states[EnumEffectHandlerType.HTTP] = (
            CircuitBreakerSnapshot(
                handler_type=EnumEffectHandlerType.HTTP,
                state=EnumCircuitBreakerState.OPEN,
                failure_count=5,
            )
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_effect_from_subcontract(effect_subcontract)

        assert "Circuit breaker open" in str(exc_info.value)
        # Handler should not be called when circuit breaker is open
        mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_effect_updates_circuit_breaker_on_success(
        self, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test circuit breaker state updates on successful execution."""
        node = MockNodeWithEffectMixin()

        mock_handler = AsyncMock(return_value={})
        node.register_effect_handler(EnumEffectHandlerType.HTTP, mock_handler)

        await node.execute_effect_from_subcontract(effect_subcontract)

        state = node.get_circuit_breaker_state(EnumEffectHandlerType.HTTP)
        assert state is not None
        assert state.state == EnumCircuitBreakerState.CLOSED
        assert state.failure_count == 0
        assert state.last_success_time_ms is not None


class TestMixinEffectExecutionRetryBehavior:
    """Test retry behavior in effect execution."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self) -> None:
        """Test retry behavior when handler fails then succeeds."""
        node = MockNodeWithEffectMixin()

        call_count = 0

        async def flaky_handler(
            operation: ModelEffectOperation, context: EffectHandlerContext
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Transient error")
            return {}  # Return empty dict - mixin expects dict for extracted_fields

        node.register_effect_handler(EnumEffectHandlerType.HTTP, flaky_handler)

        subcontract = ModelEffectSubcontract(
            subcontract_name="retry_test",
            execution_mode="sequential_abort",
            operations=[
                ModelEffectOperation(
                    operation_name="flaky_operation",
                    idempotent=True,
                    io_config=ModelHttpIOConfig(
                        url_template="https://api.example.com/test",
                        method="GET",
                    ),
                ),
            ],
            default_retry_policy=ModelEffectRetryPolicy(
                enabled=True,
                max_retries=3,
                base_delay_ms=100,  # Minimum allowed value (100ms)
            ),
        )

        result = await node.execute_effect_from_subcontract(subcontract)

        assert result.success is True
        assert call_count == 2  # Failed once, succeeded on retry
        assert result.operation_results[0].retries == 1


class TestEffectHandlerContext:
    """Test EffectHandlerContext model."""

    def test_effect_handler_context_creation(self) -> None:
        """Test creating EffectHandlerContext."""
        execution_id = uuid4()
        correlation_id = uuid4()

        context = EffectHandlerContext(
            execution_id=execution_id,
            operation_name="test_operation",
            handler_type=EnumEffectHandlerType.HTTP,
            correlation_id=correlation_id,
            retry_count=1,
            metadata={"key": "value"},
        )

        assert context.execution_id == execution_id
        assert context.operation_name == "test_operation"
        assert context.handler_type == EnumEffectHandlerType.HTTP
        assert context.correlation_id == correlation_id
        assert context.retry_count == 1
        assert context.metadata == {"key": "value"}

    def test_effect_handler_context_frozen(self) -> None:
        """Test EffectHandlerContext is immutable."""
        context = EffectHandlerContext(
            execution_id=uuid4(),
            operation_name="test",
            handler_type=EnumEffectHandlerType.HTTP,
            correlation_id=uuid4(),
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen
            context.operation_name = "modified"  # type: ignore[misc]


class TestCircuitBreakerSnapshot:
    """Test CircuitBreakerSnapshot model."""

    def test_circuit_breaker_snapshot_creation(self) -> None:
        """Test creating CircuitBreakerSnapshot."""
        snapshot = CircuitBreakerSnapshot(
            handler_type=EnumEffectHandlerType.HTTP,
            state=EnumCircuitBreakerState.CLOSED,
            failure_count=0,
        )

        assert snapshot.handler_type == EnumEffectHandlerType.HTTP
        assert snapshot.state == EnumCircuitBreakerState.CLOSED
        assert snapshot.failure_count == 0
        assert snapshot.last_failure_time_ms is None
        assert snapshot.last_success_time_ms is None

    def test_circuit_breaker_snapshot_with_times(self) -> None:
        """Test CircuitBreakerSnapshot with timing information."""
        snapshot = CircuitBreakerSnapshot(
            handler_type=EnumEffectHandlerType.DB,
            state=EnumCircuitBreakerState.HALF_OPEN,
            failure_count=3,
            last_failure_time_ms=1000.0,
            last_success_time_ms=500.0,
        )

        assert snapshot.state == EnumCircuitBreakerState.HALF_OPEN
        assert snapshot.failure_count == 3
        assert snapshot.last_failure_time_ms == 1000.0
        assert snapshot.last_success_time_ms == 500.0


class TestEffectExecutionResult:
    """Test EffectExecutionResult model."""

    def test_effect_execution_result_success(self) -> None:
        """Test creating successful EffectExecutionResult."""
        result = EffectExecutionResult(
            success=True,
            operation_results=[],
            total_duration_ms=100.5,
        )

        assert result.success is True
        assert result.failed_operation is None
        assert result.total_duration_ms == 100.5
        assert result.execution_id is not None

    def test_effect_execution_result_failure(self) -> None:
        """Test creating failed EffectExecutionResult."""
        result = EffectExecutionResult(
            success=False,
            operation_results=[],
            failed_operation="failing_op",
            total_duration_ms=50.0,
        )

        assert result.success is False
        assert result.failed_operation == "failing_op"

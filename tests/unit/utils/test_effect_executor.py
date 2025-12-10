"""
Unit tests for effect_executor module.

Tests the pure functions for executing effect operations from ModelEffectSubcontract.
Demonstrates the contract-driven, zero-custom-logic pattern for effect execution.
"""

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelDbIOConfig,
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
from omnibase_core.utils.effect_executor import (
    EffectExecutionResult,
    EffectOperationResult,
    execute_effect_operations,
    execute_single_operation,
    validate_effect_subcontract,
)


@pytest.fixture
def http_operation() -> ModelEffectOperation:
    """Create a test HTTP operation."""
    return ModelEffectOperation(
        operation_name="fetch_data",
        description="Fetch data from API",
        idempotent=True,
        io_config=ModelHttpIOConfig(
            url_template="https://api.example.com/data",
            method="GET",
            timeout_ms=5000,
        ),
    )


@pytest.fixture
def db_operation() -> ModelEffectOperation:
    """Create a test DB operation."""
    return ModelEffectOperation(
        operation_name="query_users",
        description="Query users from database",
        idempotent=True,
        io_config=ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
        ),
    )


@pytest.fixture
def retry_policy_enabled() -> ModelEffectRetryPolicy:
    """Create an enabled retry policy with minimum allowed delays for testing."""
    return ModelEffectRetryPolicy(
        enabled=True,
        max_retries=3,
        backoff_strategy="exponential",
        base_delay_ms=100,  # Minimum allowed (100ms)
        max_delay_ms=1000,  # Minimum allowed (1000ms)
        jitter_factor=0.0,  # Disable jitter for predictable tests
    )


@pytest.fixture
def retry_policy_disabled() -> ModelEffectRetryPolicy:
    """Create a disabled retry policy."""
    return ModelEffectRetryPolicy(
        enabled=False,
        max_retries=0,
    )


@pytest.fixture
def effect_subcontract_abort() -> ModelEffectSubcontract:
    """Create test effect subcontract with sequential_abort mode."""
    return ModelEffectSubcontract(
        subcontract_name="test_abort_subcontract",
        version=ModelSemVer(major=1, minor=0, patch=0),
        execution_mode="sequential_abort",
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
            ModelEffectOperation(
                operation_name="operation_3",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/op3",
                    method="GET",
                ),
            ),
        ],
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=False,
        ),
    )


@pytest.fixture
def effect_subcontract_continue() -> ModelEffectSubcontract:
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
            ModelEffectOperation(
                operation_name="operation_3",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/op3",
                    method="GET",
                ),
            ),
        ],
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=False,
        ),
    )


class TestValidateEffectSubcontract:
    """Test validate_effect_subcontract pure function."""

    @pytest.mark.asyncio
    async def test_validate_valid_subcontract(
        self, effect_subcontract_abort: ModelEffectSubcontract
    ) -> None:
        """Test validation passes for valid subcontract."""
        errors = await validate_effect_subcontract(effect_subcontract_abort)

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_duplicate_operation_names(self) -> None:
        """Test validation fails for duplicate operation names."""
        subcontract = ModelEffectSubcontract(
            subcontract_name="duplicate_test",
            execution_mode="sequential_abort",
            operations=[
                ModelEffectOperation(
                    operation_name="same_name",
                    idempotent=True,
                    io_config=ModelHttpIOConfig(
                        url_template="https://api.example.com/op1",
                        method="GET",
                    ),
                ),
                ModelEffectOperation(
                    operation_name="same_name",  # Duplicate!
                    idempotent=True,
                    io_config=ModelHttpIOConfig(
                        url_template="https://api.example.com/op2",
                        method="GET",
                    ),
                ),
            ],
        )

        errors = await validate_effect_subcontract(subcontract)

        assert len(errors) > 0
        assert any("Duplicate operation names" in error for error in errors)


class TestExecuteSingleOperation:
    """Test execute_single_operation pure function."""

    @pytest.mark.asyncio
    async def test_execute_single_operation_success(
        self,
        http_operation: ModelEffectOperation,
        retry_policy_disabled: ModelEffectRetryPolicy,
    ) -> None:
        """Test successful single operation execution."""
        handler = AsyncMock(return_value={"status_code": 200, "data": "test"})

        result = await execute_single_operation(
            operation=http_operation,
            context={"base_url": "https://api.example.com"},
            handler=handler,
            retry_policy=retry_policy_disabled,
        )

        assert isinstance(result, EffectOperationResult)
        assert result.success is True
        assert result.operation_name == "fetch_data"
        assert result.result == {"status_code": 200, "data": "test"}
        assert result.error is None
        assert result.retry_count == 0
        assert result.processing_time_ms > 0
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_operation_failure_no_retry(
        self,
        http_operation: ModelEffectOperation,
        retry_policy_disabled: ModelEffectRetryPolicy,
    ) -> None:
        """Test single operation failure without retry."""
        handler = AsyncMock(side_effect=ValueError("Handler error"))

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=handler,
            retry_policy=retry_policy_disabled,
        )

        assert result.success is False
        assert result.error == "Handler error"
        assert result.retry_count == 0
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_operation_with_retry_success(
        self,
        http_operation: ModelEffectOperation,
        retry_policy_enabled: ModelEffectRetryPolicy,
    ) -> None:
        """Test single operation succeeds after retry.

        Note: retry_count in the result represents the number of retries that occurred
        before success. When the handler fails once and succeeds on retry, the
        retry_count returned on success is the attempt number of the last failure (0).
        """
        call_count = 0

        async def flaky_handler(
            operation: ModelEffectOperation, context: dict[str, Any]
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:  # Fail on first attempt only
                raise ValueError("Transient error")
            return {"success": True}

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=flaky_handler,
            retry_policy=retry_policy_enabled,
        )

        assert result.success is True
        # retry_count captures failures: when first attempt (0) fails, retry_count=0
        # When second attempt succeeds, we return the success with retry_count from the failure
        assert result.retry_count == 0
        assert call_count == 2  # Called twice: one failure, one success

    @pytest.mark.asyncio
    async def test_execute_single_operation_exhausted_retries(
        self,
        http_operation: ModelEffectOperation,
        retry_policy_enabled: ModelEffectRetryPolicy,
    ) -> None:
        """Test single operation fails after exhausting retries."""
        handler = AsyncMock(side_effect=ValueError("Persistent error"))

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=handler,
            retry_policy=retry_policy_enabled,
        )

        assert result.success is False
        assert result.error == "Persistent error"
        assert result.retry_count == 3  # max_retries attempts
        assert handler.call_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_execute_single_operation_sync_handler(
        self,
        http_operation: ModelEffectOperation,
        retry_policy_disabled: ModelEffectRetryPolicy,
    ) -> None:
        """Test execution with synchronous handler."""

        def sync_handler(
            operation: ModelEffectOperation, context: dict[str, Any]
        ) -> dict[str, Any]:
            return {"sync": True}

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=sync_handler,
            retry_policy=retry_policy_disabled,
        )

        assert result.success is True
        assert result.result == {"sync": True}


class TestExecuteEffectOperationsAbortMode:
    """Test execute_effect_operations with sequential_abort mode."""

    @pytest.mark.asyncio
    async def test_execute_all_operations_success(
        self, effect_subcontract_abort: ModelEffectSubcontract
    ) -> None:
        """Test all operations execute successfully in abort mode."""
        handler = AsyncMock(return_value={"status": "ok"})

        result = await execute_effect_operations(
            subcontract=effect_subcontract_abort,
            context={},
            handler_registry={"http": handler},
        )

        assert isinstance(result, EffectExecutionResult)
        assert result.success is True
        assert len(result.results) == 3
        assert result.failed_operation is None
        assert result.total_time_ms > 0
        assert handler.call_count == 3

    @pytest.mark.asyncio
    async def test_abort_on_first_failure(
        self, effect_subcontract_abort: ModelEffectSubcontract
    ) -> None:
        """Test execution stops on first failure in abort mode."""
        call_count = 0

        async def handler_fails_second(
            operation: ModelEffectOperation, context: dict[str, Any]
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if operation.operation_name == "operation_2":
                raise ValueError("Second operation fails")
            return {"success": True}

        with pytest.raises(ModelOnexError) as exc_info:
            await execute_effect_operations(
                subcontract=effect_subcontract_abort,
                context={},
                handler_registry={"http": handler_fails_second},
            )

        # Error message contains the original exception message
        assert "Second operation fails" in str(exc_info.value)
        # Should have executed op1 (success) and op2 (failed), but not op3
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_abort_missing_handler(
        self, effect_subcontract_abort: ModelEffectSubcontract
    ) -> None:
        """Test execution fails immediately with missing handler in abort mode."""
        # Empty handler registry
        with pytest.raises(ModelOnexError) as exc_info:
            await execute_effect_operations(
                subcontract=effect_subcontract_abort,
                context={},
                handler_registry={},
            )

        assert "No handler registered" in str(exc_info.value)


class TestExecuteEffectOperationsContinueMode:
    """Test execute_effect_operations with sequential_continue mode."""

    @pytest.mark.asyncio
    async def test_execute_all_operations_success(
        self, effect_subcontract_continue: ModelEffectSubcontract
    ) -> None:
        """Test all operations execute successfully in continue mode."""
        handler = AsyncMock(return_value={"status": "ok"})

        result = await execute_effect_operations(
            subcontract=effect_subcontract_continue,
            context={},
            handler_registry={"http": handler},
        )

        assert result.success is True
        assert len(result.results) == 3
        assert all(r.success for r in result.results)
        assert result.failed_operation is None

    @pytest.mark.asyncio
    async def test_continue_after_failure(
        self, effect_subcontract_continue: ModelEffectSubcontract
    ) -> None:
        """Test execution continues after failure in continue mode."""
        call_count = 0

        async def handler_fails_second(
            operation: ModelEffectOperation, context: dict[str, Any]
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if operation.operation_name == "operation_2":
                raise ValueError("Second operation fails")
            return {"success": True}

        result = await execute_effect_operations(
            subcontract=effect_subcontract_continue,
            context={},
            handler_registry={"http": handler_fails_second},
        )

        # Should NOT raise, just return result with failure info
        assert result.success is False
        assert len(result.results) == 3
        assert result.results[0].success is True
        assert result.results[1].success is False
        assert result.results[2].success is True
        assert result.failed_operation == "operation_2"
        assert call_count == 3  # All operations executed

    @pytest.mark.asyncio
    async def test_continue_multiple_failures(
        self, effect_subcontract_continue: ModelEffectSubcontract
    ) -> None:
        """Test execution continues with multiple failures in continue mode."""

        async def handler_fails_odd(
            operation: ModelEffectOperation, context: dict[str, Any]
        ) -> dict[str, Any]:
            if operation.operation_name in ("operation_1", "operation_3"):
                raise ValueError(f"{operation.operation_name} fails")
            return {"success": True}

        result = await execute_effect_operations(
            subcontract=effect_subcontract_continue,
            context={},
            handler_registry={"http": handler_fails_odd},
        )

        assert result.success is False
        assert result.results[0].success is False
        assert result.results[1].success is True
        assert result.results[2].success is False
        # failed_operation should be the FIRST failed operation
        assert result.failed_operation == "operation_1"

    @pytest.mark.asyncio
    async def test_continue_missing_handler(
        self, effect_subcontract_continue: ModelEffectSubcontract
    ) -> None:
        """Test execution continues with missing handler in continue mode."""
        result = await execute_effect_operations(
            subcontract=effect_subcontract_continue,
            context={},
            handler_registry={},  # Empty - no handlers
        )

        assert result.success is False
        assert len(result.results) == 3
        assert all(not r.success for r in result.results)
        assert all("No handler registered" in (r.error or "") for r in result.results)


class TestExecuteEffectOperationsCorrelation:
    """Test correlation ID handling in effect execution."""

    @pytest.mark.asyncio
    async def test_correlation_id_preserved(
        self, effect_subcontract_abort: ModelEffectSubcontract
    ) -> None:
        """Test correlation ID is preserved in execution result."""
        handler = AsyncMock(return_value={"status": "ok"})

        result = await execute_effect_operations(
            subcontract=effect_subcontract_abort,
            context={},
            handler_registry={"http": handler},
        )

        assert result.correlation_id == effect_subcontract_abort.correlation_id

    @pytest.mark.asyncio
    async def test_custom_correlation_id(self) -> None:
        """Test execution with custom correlation ID."""
        custom_correlation_id = uuid4()
        subcontract = ModelEffectSubcontract(
            subcontract_name="correlation_test",
            execution_mode="sequential_abort",
            correlation_id=custom_correlation_id,
            operations=[
                ModelEffectOperation(
                    operation_name="test_op",
                    idempotent=True,
                    io_config=ModelHttpIOConfig(
                        url_template="https://api.example.com/test",
                        method="GET",
                    ),
                ),
            ],
        )

        handler = AsyncMock(return_value={"status": "ok"})

        result = await execute_effect_operations(
            subcontract=subcontract,
            context={},
            handler_registry={"http": handler},
        )

        assert result.correlation_id == custom_correlation_id


class TestEffectOperationResult:
    """Test EffectOperationResult dataclass."""

    def test_operation_result_success(self) -> None:
        """Test creating successful operation result."""
        result = EffectOperationResult(
            operation_name="test_op",
            success=True,
            result={"data": "value"},
            error=None,
            retry_count=0,
            processing_time_ms=50.5,
        )

        assert result.operation_name == "test_op"
        assert result.success is True
        assert result.result == {"data": "value"}
        assert result.error is None
        assert result.retry_count == 0
        assert result.processing_time_ms == 50.5

    def test_operation_result_failure(self) -> None:
        """Test creating failed operation result."""
        result = EffectOperationResult(
            operation_name="failed_op",
            success=False,
            result=None,
            error="Connection timeout",
            retry_count=3,
            processing_time_ms=30000.0,
        )

        assert result.success is False
        assert result.result is None
        assert result.error == "Connection timeout"
        assert result.retry_count == 3


class TestEffectExecutionResult:
    """Test EffectExecutionResult dataclass."""

    def test_execution_result_success(self) -> None:
        """Test creating successful execution result."""
        result = EffectExecutionResult(
            success=True,
            results=[
                EffectOperationResult(
                    operation_name="op1",
                    success=True,
                    result={"data": 1},
                    error=None,
                    retry_count=0,
                    processing_time_ms=10.0,
                ),
            ],
            failed_operation=None,
            total_time_ms=100.0,
        )

        assert result.success is True
        assert len(result.results) == 1
        assert result.failed_operation is None
        assert result.total_time_ms == 100.0
        assert result.correlation_id is not None  # Default generated

    def test_execution_result_failure(self) -> None:
        """Test creating failed execution result."""
        custom_correlation = uuid4()
        result = EffectExecutionResult(
            success=False,
            results=[],
            failed_operation="failing_op",
            total_time_ms=50.0,
            correlation_id=custom_correlation,
        )

        assert result.success is False
        assert result.failed_operation == "failing_op"
        assert result.correlation_id == custom_correlation


class TestRetryBackoffStrategies:
    """Test different retry backoff strategies."""

    @pytest.mark.asyncio
    async def test_fixed_backoff(self, http_operation: ModelEffectOperation) -> None:
        """Test fixed backoff strategy."""
        policy = ModelEffectRetryPolicy(
            enabled=True,
            max_retries=2,
            backoff_strategy="fixed",
            base_delay_ms=100,  # Minimum allowed (100ms)
            jitter_factor=0.0,
        )

        handler = AsyncMock(side_effect=ValueError("error"))

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=handler,
            retry_policy=policy,
        )

        assert result.success is False
        assert handler.call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_linear_backoff(self, http_operation: ModelEffectOperation) -> None:
        """Test linear backoff strategy."""
        policy = ModelEffectRetryPolicy(
            enabled=True,
            max_retries=2,
            backoff_strategy="linear",
            base_delay_ms=100,  # Minimum allowed (100ms)
            jitter_factor=0.0,
        )

        handler = AsyncMock(side_effect=ValueError("error"))

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=handler,
            retry_policy=policy,
        )

        assert result.success is False
        assert handler.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff(
        self, http_operation: ModelEffectOperation
    ) -> None:
        """Test exponential backoff strategy."""
        policy = ModelEffectRetryPolicy(
            enabled=True,
            max_retries=2,
            backoff_strategy="exponential",
            base_delay_ms=100,  # Minimum allowed (100ms)
            jitter_factor=0.0,
        )

        handler = AsyncMock(side_effect=ValueError("error"))

        result = await execute_single_operation(
            operation=http_operation,
            context={},
            handler=handler,
            retry_policy=policy,
        )

        assert result.success is False
        assert handler.call_count == 3


class TestContextPassthrough:
    """Test context is correctly passed to handlers."""

    @pytest.mark.asyncio
    async def test_context_passed_to_handler(
        self, effect_subcontract_abort: ModelEffectSubcontract
    ) -> None:
        """Test execution context is passed to all handlers."""
        captured_contexts: list[dict[str, Any]] = []

        async def capturing_handler(
            operation: ModelEffectOperation, context: dict[str, Any]
        ) -> dict[str, Any]:
            captured_contexts.append(context.copy())
            return {"captured": True}

        test_context = {
            "user_id": "123",
            "session_token": "abc",
            "feature_flags": {"new_ui": True},
        }

        await execute_effect_operations(
            subcontract=effect_subcontract_abort,
            context=test_context,
            handler_registry={"http": capturing_handler},
        )

        assert len(captured_contexts) == 3
        for ctx in captured_contexts:
            assert ctx == test_context

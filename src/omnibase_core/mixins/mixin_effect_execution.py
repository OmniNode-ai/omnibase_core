"""
Mixin for effect execution from YAML contracts.

Enables effect nodes to execute declarative I/O operations from ModelEffectSubcontract.

Typing: Strongly typed with strategic Any usage for mixin kwargs and handler context.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.contracts.subcontracts.model_effect_operation_result import (
    ModelEffectOperationResult,
)
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)


class EffectExecutionResult(BaseModel):
    """
    Result of effect subcontract execution.

    Captures success/failure, operation results, and circuit breaker states.

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool = Field(description="True if all operations succeeded")
    execution_id: UUID = Field(default_factory=uuid4, description="Unique execution ID")
    operation_results: list[ModelEffectOperationResult] = Field(
        default_factory=list, description="Results of each operation"
    )
    failed_operation: str | None = Field(
        default=None, description="Name of first failed operation, if any"
    )
    total_duration_ms: float = Field(
        default=0.0, ge=0, description="Total execution time"
    )
    circuit_breaker_states: dict[str, EnumCircuitBreakerState] = Field(
        default_factory=dict, description="Circuit breaker states by handler type"
    )


class EffectHandlerContext(BaseModel):
    """
    Context passed to effect handlers during execution.

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: UUID = Field(description="Unique execution ID")
    operation_name: str = Field(description="Name of the operation being executed")
    handler_type: EnumEffectHandlerType = Field(description="Type of effect handler")
    correlation_id: UUID = Field(description="Correlation ID for tracing")
    retry_count: int = Field(default=0, ge=0, description="Current retry attempt")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata"
    )


# Type alias for effect handler functions
EffectHandler = Any  # Callable[[ModelEffectOperation, EffectHandlerContext], Awaitable[ModelEffectOperationResult]]


class CircuitBreakerSnapshot(BaseModel):
    """
    Snapshot of circuit breaker state for a handler type.

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_type: EnumEffectHandlerType = Field(description="Handler type")
    state: EnumCircuitBreakerState = Field(description="Current circuit breaker state")
    failure_count: int = Field(
        default=0, ge=0, description="Number of consecutive failures"
    )
    last_failure_time_ms: float | None = Field(
        default=None, description="Timestamp of last failure"
    )
    last_success_time_ms: float | None = Field(
        default=None, description="Timestamp of last success"
    )


class MixinEffectExecution:
    """
    Mixin providing effect execution capabilities from YAML contracts.

    Enables effect nodes to execute I/O operations declaratively without
    custom code. Effect execution is driven entirely by ModelEffectSubcontract.

    Usage:
        class NodeMyEffect(NodeEffect, MixinEffectExecution):
            # No custom effect execution code needed - driven by YAML contract
            pass

    Pattern:
        This mixin maintains minimal state (handler registry, circuit breaker states).
        Execution is delegated to registered handlers per effect handler type.
        Supports retry policies and circuit breaker patterns from subcontract.

    .. versionadded:: 0.4.0
        Mixin-based effect execution for declarative I/O operations.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize effect execution mixin.

        Args:
            **kwargs: Passed to super().__init__()
        """
        super().__init__(**kwargs)

        # Handler registry: maps handler type to callable
        # Uses Any type as handlers are callables with complex signatures
        self._effect_handlers: dict[EnumEffectHandlerType, EffectHandler] = {}

        # Circuit breaker states per handler type
        self._circuit_breaker_states: dict[
            EnumEffectHandlerType, CircuitBreakerSnapshot
        ] = {}

    async def execute_effect_from_subcontract(
        self,
        subcontract: ModelEffectSubcontract,
        context: dict[str, Any] | None = None,
    ) -> EffectExecutionResult:
        """
        Execute effect operations from YAML subcontract.

        Executes all operations in the subcontract according to the specified
        execution_mode (sequential_abort or sequential_continue).

        Args:
            subcontract: Effect subcontract from node contract
            context: Optional execution context data

        Returns:
            EffectExecutionResult with operation results and status

        Raises:
            ModelOnexError: If execution_mode is sequential_abort and operation fails

        Example:
            result = await self.execute_effect_from_subcontract(
                self.contract.io_operations,
                context={"batch_id": "123"},
            )

            if result.success:
                print(f"All {len(result.operation_results)} operations succeeded")
            else:
                print(f"Failed at operation: {result.failed_operation}")
        """
        import time

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        start_time = time.perf_counter()
        execution_id = uuid4()
        operation_results: list[ModelEffectOperationResult] = []
        failed_operation: str | None = None
        context = context or {}

        for operation in subcontract.operations:
            op_start = time.perf_counter()

            # Build handler context
            handler_context = EffectHandlerContext(
                execution_id=execution_id,
                operation_name=operation.operation_name,
                handler_type=EnumEffectHandlerType(operation.handler_type),
                correlation_id=subcontract.correlation_id,
                metadata=context,
            )

            # Check circuit breaker
            handler_type = EnumEffectHandlerType(operation.handler_type)
            cb_snapshot = self._circuit_breaker_states.get(handler_type)
            if cb_snapshot and cb_snapshot.state == EnumCircuitBreakerState.OPEN:
                # Circuit breaker is open - fail fast
                op_result = ModelEffectOperationResult(
                    operation_name=operation.operation_name,
                    success=False,
                    retries=0,
                    duration_ms=(time.perf_counter() - op_start) * 1000,
                    extracted_fields={},
                    error_message=f"Circuit breaker open for handler type: {handler_type.value}",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED.value,
                )
                operation_results.append(op_result)

                if subcontract.execution_mode == "sequential_abort":
                    failed_operation = operation.operation_name
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        message=f"Circuit breaker open for {handler_type.value}",
                        context={
                            "operation_name": operation.operation_name,
                            "handler_type": handler_type.value,
                        },
                    )
                continue

            # Check if handler is registered
            handler = self._effect_handlers.get(handler_type)
            if handler is None:
                op_result = ModelEffectOperationResult(
                    operation_name=operation.operation_name,
                    success=False,
                    retries=0,
                    duration_ms=(time.perf_counter() - op_start) * 1000,
                    extracted_fields={},
                    error_message=f"No handler registered for type: {handler_type.value}",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED.value,
                )
                operation_results.append(op_result)

                if subcontract.execution_mode == "sequential_abort":
                    failed_operation = operation.operation_name
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        message=f"No handler registered for effect type: {handler_type.value}",
                        context={
                            "operation_name": operation.operation_name,
                            "handler_type": handler_type.value,
                        },
                    )
                continue

            # Execute handler with retry logic
            retry_policy = operation.retry_policy or subcontract.default_retry_policy
            max_retries = retry_policy.max_retries if retry_policy.enabled else 0
            retry_count = 0
            success = False
            error_message: str | None = None

            while retry_count <= max_retries:
                try:
                    # Execute the handler
                    result = await handler(operation, handler_context)
                    success = True

                    # Record success in circuit breaker
                    self._record_circuit_breaker_success(handler_type)

                    op_result = ModelEffectOperationResult(
                        operation_name=operation.operation_name,
                        success=True,
                        retries=retry_count,
                        duration_ms=(time.perf_counter() - op_start) * 1000,
                        extracted_fields=(result if isinstance(result, dict) else {}),
                    )
                    operation_results.append(op_result)
                    break

                except Exception as e:
                    error_message = str(e)
                    retry_count += 1

                    if retry_count > max_retries:
                        # Record failure in circuit breaker
                        self._record_circuit_breaker_failure(handler_type)

                        op_result = ModelEffectOperationResult(
                            operation_name=operation.operation_name,
                            success=False,
                            retries=retry_count - 1,
                            duration_ms=(time.perf_counter() - op_start) * 1000,
                            extracted_fields={},
                            error_message=error_message,
                            error_code=EnumCoreErrorCode.OPERATION_FAILED.value,
                        )
                        operation_results.append(op_result)

                        if subcontract.execution_mode == "sequential_abort":
                            failed_operation = operation.operation_name
                            raise ModelOnexError(
                                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                                message=f"Effect operation failed: {error_message}",
                                context={
                                    "operation_name": operation.operation_name,
                                    "handler_type": handler_type.value,
                                    "retries": retry_count - 1,
                                },
                            ) from e
                        break

                    # Wait before retry (exponential backoff)
                    import asyncio

                    delay_ms = retry_policy.base_delay_ms * (2 ** (retry_count - 1))
                    await asyncio.sleep(delay_ms / 1000.0)

            if not success and failed_operation is None:
                failed_operation = operation.operation_name

        total_duration_ms = (time.perf_counter() - start_time) * 1000
        overall_success = all(r.success for r in operation_results)

        return EffectExecutionResult(
            success=overall_success,
            execution_id=execution_id,
            operation_results=operation_results,
            failed_operation=failed_operation if not overall_success else None,
            total_duration_ms=total_duration_ms,
            circuit_breaker_states={
                k.value: v.state for k, v in self._circuit_breaker_states.items()
            },
        )

    async def validate_effect_subcontract(
        self, subcontract: ModelEffectSubcontract
    ) -> list[str]:
        """
        Validate effect subcontract for correctness.

        Checks:
        - All operations have registered handlers
        - Circuit breakers are not open for required handler types
        - Retry policies are valid for idempotent operations

        Args:
            subcontract: Effect subcontract to validate

        Returns:
            List of validation errors (empty if valid)

        Example:
            errors = await self.validate_effect_subcontract(
                self.contract.io_operations
            )

            if errors:
                print(f"Subcontract validation failed: {errors}")
            else:
                print("Effect subcontract is valid!")
        """
        errors: list[str] = []

        # Check all operations have handlers
        for operation in subcontract.operations:
            handler_type = EnumEffectHandlerType(operation.handler_type)

            if handler_type not in self._effect_handlers:
                errors.append(
                    f"No handler registered for type '{handler_type.value}' "
                    f"(operation: {operation.operation_name})"
                )

            # Check circuit breaker state
            cb_snapshot = self._circuit_breaker_states.get(handler_type)
            if cb_snapshot and cb_snapshot.state == EnumCircuitBreakerState.OPEN:
                errors.append(
                    f"Circuit breaker open for type '{handler_type.value}' "
                    f"(operation: {operation.operation_name})"
                )

        # Validate retry policies (handled by subcontract's own validators)
        # Additional custom validation can be added here

        return errors

    def register_effect_handler(
        self,
        handler_type: EnumEffectHandlerType,
        handler: EffectHandler,
    ) -> None:
        """
        Register an effect handler for a specific handler type.

        Args:
            handler_type: Type of effect to handle (HTTP, DB, KAFKA, FILESYSTEM)
            handler: Async callable that executes the effect operation

        Example:
            async def http_handler(operation, context):
                # Execute HTTP operation
                return {"status_code": 200}

            self.register_effect_handler(
                EnumEffectHandlerType.HTTP,
                http_handler
            )
        """
        self._effect_handlers[handler_type] = handler

        # Initialize circuit breaker for this handler type if not exists
        if handler_type not in self._circuit_breaker_states:
            self._circuit_breaker_states[handler_type] = CircuitBreakerSnapshot(
                handler_type=handler_type,
                state=EnumCircuitBreakerState.CLOSED,
                failure_count=0,
            )

    def get_registered_handlers(self) -> list[EnumEffectHandlerType]:
        """
        Get list of registered effect handler types.

        Returns:
            List of EnumEffectHandlerType values that have handlers registered

        Example:
            handlers = self.get_registered_handlers()
            print(f"Registered handlers: {[h.value for h in handlers]}")
        """
        return list(self._effect_handlers.keys())

    def get_circuit_breaker_state(
        self, handler_type: EnumEffectHandlerType
    ) -> CircuitBreakerSnapshot | None:
        """
        Get circuit breaker state for a handler type.

        Args:
            handler_type: Handler type to check

        Returns:
            CircuitBreakerSnapshot or None if no state exists

        Example:
            state = self.get_circuit_breaker_state(EnumEffectHandlerType.HTTP)
            if state and state.state == EnumCircuitBreakerState.OPEN:
                print("HTTP circuit breaker is open!")
        """
        return self._circuit_breaker_states.get(handler_type)

    def reset_circuit_breaker(self, handler_type: EnumEffectHandlerType) -> None:
        """
        Reset circuit breaker for a handler type to closed state.

        Args:
            handler_type: Handler type to reset

        Example:
            # After recovering from failures
            self.reset_circuit_breaker(EnumEffectHandlerType.HTTP)
        """
        import time

        self._circuit_breaker_states[handler_type] = CircuitBreakerSnapshot(
            handler_type=handler_type,
            state=EnumCircuitBreakerState.CLOSED,
            failure_count=0,
            last_success_time_ms=time.perf_counter() * 1000,
        )

    def _record_circuit_breaker_success(
        self, handler_type: EnumEffectHandlerType
    ) -> None:
        """Record a successful operation for circuit breaker tracking."""
        import time

        current = self._circuit_breaker_states.get(handler_type)

        self._circuit_breaker_states[handler_type] = CircuitBreakerSnapshot(
            handler_type=handler_type,
            state=EnumCircuitBreakerState.CLOSED,
            failure_count=0,
            last_success_time_ms=time.perf_counter() * 1000,
            last_failure_time_ms=(current.last_failure_time_ms if current else None),
        )

    def _record_circuit_breaker_failure(
        self, handler_type: EnumEffectHandlerType
    ) -> None:
        """Record a failed operation for circuit breaker tracking."""
        import time

        current = self._circuit_breaker_states.get(handler_type)
        failure_count = (current.failure_count + 1) if current else 1

        # Default threshold for opening circuit breaker
        # This can be configured via subcontract circuit breaker settings
        failure_threshold = 5

        new_state = (
            EnumCircuitBreakerState.OPEN
            if failure_count >= failure_threshold
            else EnumCircuitBreakerState.CLOSED
        )

        self._circuit_breaker_states[handler_type] = CircuitBreakerSnapshot(
            handler_type=handler_type,
            state=new_state,
            failure_count=failure_count,
            last_failure_time_ms=time.perf_counter() * 1000,
            last_success_time_ms=(current.last_success_time_ms if current else None),
        )

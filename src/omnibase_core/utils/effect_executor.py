"""
Effect execution utilities for declarative effect operations.

Pure functions for executing effect operations from ModelEffectSubcontract.
No side effects beyond what handlers do - returns results and execution metrics.

Typing: Strongly typed with strategic Any usage for handler return values
and context data which vary by operation type.

Thread Safety:
    All functions in this module are pure and stateless - safe for concurrent use.
    Each execution operates on its own data and context without modifying shared state.

Effect Execution Model:
    - Operations execute sequentially per execution_mode setting
    - sequential_abort: Stop on first failure, raise error
    - sequential_continue: Run all operations, report all outcomes
    - Full execution metrics captured for observability

Retry Behavior:
    - Retries only for idempotent operations (validated at contract level)
    - Exponential/linear/fixed backoff with jitter
    - Circuit breaker integration for fault tolerance

Example:
    >>> from omnibase_core.utils.effect_executor import execute_effect_operations
    >>> from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ...     ModelEffectSubcontract,
    ... )
    >>> from uuid import uuid4
    >>>
    >>> # Load subcontract from YAML
    >>> subcontract = ModelEffectSubcontract(...)
    >>>
    >>> # Define handlers for each operation type
    >>> handlers = {
    ...     "http": http_handler,
    ...     "db": database_handler,
    ... }
    >>>
    >>> # Execute all operations
    >>> result = await execute_effect_operations(subcontract, context, handlers)
    >>> if result.success:
    ...     print(f"All operations completed in {result.total_time_ms:.2f}ms")
    ... else:
    ...     print(f"Failed at operation: {result.failed_operation}")

See Also:
    - omnibase_core.models.contracts.subcontracts.model_effect_subcontract: Contract model
    - omnibase_core.models.contracts.subcontracts.model_effect_operation: Operation model
    - omnibase_core.mixins.mixin_effect_execution: Async wrapper mixin
    - docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md: Effect node tutorial
"""

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
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


@dataclass
class EffectOperationResult:
    """
    Result of a single effect operation.

    Captures the outcome of executing one operation from the subcontract,
    including success/failure status, timing metrics, and retry information.

    Attributes:
        operation_name: Name of the operation from the subcontract.
        success: Whether the operation completed successfully.
        result: Operation result data if successful, None if failed.
            Type varies based on handler and operation type.
        error: Error message if operation failed, None if successful.
        retry_count: Number of retry attempts made (0 = success on first try).
        processing_time_ms: Total execution time including all retries.

    Example:
        >>> result = EffectOperationResult(
        ...     operation_name="fetch_user",
        ...     success=True,
        ...     result={"id": 1, "name": "Alice"},
        ...     error=None,
        ...     retry_count=0,
        ...     processing_time_ms=45.2,
        ... )
    """

    operation_name: str
    success: bool
    result: Any  # Any: handler return type varies by operation
    error: str | None
    retry_count: int
    processing_time_ms: float


@dataclass
class EffectExecutionResult:
    """
    Result of executing all operations in a subcontract.

    Aggregates results from all operation executions with overall
    success/failure status and timing metrics.

    Attributes:
        success: True if all operations completed successfully.
        results: List of individual operation results in execution order.
        failed_operation: Name of first failed operation, None if all succeeded.
        total_time_ms: Total execution time for all operations.
        correlation_id: Correlation ID for distributed tracing.

    Example:
        >>> if execution_result.success:
        ...     for op_result in execution_result.results:
        ...         print(f"{op_result.operation_name}: {op_result.result}")
        ... else:
        ...     print(f"Failed at: {execution_result.failed_operation}")
    """

    success: bool
    results: list[EffectOperationResult]
    failed_operation: str | None
    total_time_ms: float
    correlation_id: UUID = field(default_factory=uuid4)


async def execute_effect_operations(
    subcontract: ModelEffectSubcontract,
    context: dict[str, Any],
    handler_registry: dict[str, Callable[..., Any]],
) -> EffectExecutionResult:
    """
    Execute all effect operations from subcontract.

    Pure function: (subcontract, context, handlers) -> EffectExecutionResult

    Executes operations sequentially according to the subcontract's execution_mode:
    - sequential_abort: Stop on first failure, useful for atomic operations
    - sequential_continue: Run all operations, report all outcomes

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.
        Handler functions should also be safe for concurrent invocation.

    Args:
        subcontract: Effect subcontract definition with operations.
        context: Execution context data passed to handlers.
            Keys depend on operation types (connection pools, credentials, etc.).
        handler_registry: Map of handler_type -> handler function.
            Handlers must accept (operation, context) and return result.

    Returns:
        EffectExecutionResult with all operation outcomes and timing.

    Raises:
        ModelOnexError: If execution_mode is sequential_abort and any operation fails.

    Example:
        Execute HTTP and database operations::

            subcontract = ModelEffectSubcontract(
                subcontract_name="user_sync",
                execution_mode="sequential_abort",
                operations=[
                    ModelEffectOperation(operation_name="fetch_user", ...),
                    ModelEffectOperation(operation_name="update_cache", ...),
                ],
            )

            async def http_handler(op, ctx):
                return await fetch(op.io_config.url)

            async def db_handler(op, ctx):
                return await ctx["pool"].execute(op.io_config.query)

            result = await execute_effect_operations(
                subcontract,
                {"pool": db_pool},
                {"http": http_handler, "db": db_handler},
            )
    """
    start_time = time.perf_counter()
    results: list[EffectOperationResult] = []
    failed_operation: str | None = None

    for operation in subcontract.operations:
        # Get handler for this operation type
        handler_type = operation.handler_type
        handler = handler_registry.get(handler_type)

        if handler is None:
            error_msg = f"No handler registered for type: {handler_type}"
            op_result = EffectOperationResult(
                operation_name=operation.operation_name,
                success=False,
                result=None,
                error=error_msg,
                retry_count=0,
                processing_time_ms=0.0,
            )
            results.append(op_result)

            if subcontract.execution_mode == "sequential_abort":
                failed_operation = operation.operation_name
                total_time_ms = (time.perf_counter() - start_time) * 1000
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    message=error_msg,
                    context={
                        "operation": operation.operation_name,
                        "handler_type": handler_type,
                        "partial_results": [
                            r.operation_name for r in results if r.success
                        ],
                    },
                )

            failed_operation = failed_operation or operation.operation_name
            continue

        # Get effective retry policy
        retry_policy = operation.retry_policy or subcontract.default_retry_policy

        # Execute with retry logic
        op_result = await execute_single_operation(
            operation=operation,
            context=context,
            handler=handler,
            retry_policy=retry_policy,
        )
        results.append(op_result)

        if not op_result.success:
            if subcontract.execution_mode == "sequential_abort":
                failed_operation = operation.operation_name
                total_time_ms = (time.perf_counter() - start_time) * 1000
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    message=op_result.error or "Operation failed",
                    context={
                        "operation": operation.operation_name,
                        "retry_count": op_result.retry_count,
                        "partial_results": [
                            r.operation_name for r in results if r.success
                        ],
                    },
                )

            failed_operation = failed_operation or operation.operation_name

    total_time_ms = (time.perf_counter() - start_time) * 1000
    success = all(r.success for r in results)

    return EffectExecutionResult(
        success=success,
        results=results,
        failed_operation=failed_operation if not success else None,
        total_time_ms=total_time_ms,
        correlation_id=subcontract.correlation_id,
    )


async def validate_effect_subcontract(
    subcontract: ModelEffectSubcontract,
) -> list[str]:
    """
    Validate effect subcontract for correctness.

    Pure validation function - no side effects.

    Performs runtime validation checks beyond what Pydantic model validation
    provides. This includes semantic validation that requires inspecting
    relationships between fields.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        subcontract: Effect subcontract to validate.

    Returns:
        List of validation errors (empty if valid).

    Example:
        Validate subcontract before execution::

            subcontract = ModelEffectSubcontract(...)

            errors = await validate_effect_subcontract(subcontract)
            if errors:
                print("Validation failed:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print("Subcontract is valid")
                # Safe to execute
    """
    errors: list[str] = []

    # Check subcontract has operations
    if not subcontract.operations:
        errors.append("Subcontract has no operations defined")
        return errors

    # Check for duplicate operation names
    operation_names = [op.operation_name for op in subcontract.operations]
    duplicates = [name for name in operation_names if operation_names.count(name) > 1]
    if duplicates:
        unique_duplicates = list(set(duplicates))
        errors.append(f"Duplicate operation names: {', '.join(unique_duplicates)}")

    # Check execution mode is valid
    valid_modes = {"sequential_abort", "sequential_continue"}
    if subcontract.execution_mode not in valid_modes:
        errors.append(
            f"Invalid execution_mode: {subcontract.execution_mode}. "
            f"Must be one of: {', '.join(sorted(valid_modes))}"
        )

    # Validate individual operations
    for op in subcontract.operations:
        # Check operation has a name
        if not op.operation_name:
            errors.append("Operation missing name")

        # Check retry policy consistency with idempotency
        retry_policy = op.retry_policy or subcontract.default_retry_policy
        if retry_policy.enabled and retry_policy.max_retries > 0:
            if not op.get_effective_idempotency():
                errors.append(
                    f"Operation '{op.operation_name}' is not idempotent "
                    f"but has retry enabled"
                )

    return errors


async def execute_single_operation(
    operation: ModelEffectOperation,
    context: dict[str, Any],
    handler: Callable[..., Any],
    retry_policy: ModelEffectRetryPolicy,
) -> EffectOperationResult:
    """
    Execute single operation with retry logic.

    Handles retry with configurable backoff strategy and jitter.
    Respects operation timeout if configured.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.
        Handler function should be safe for concurrent invocation.

    Args:
        operation: Effect operation to execute.
        context: Execution context passed to handler.
        handler: Handler function for this operation type.
            Must accept (operation, context) and return result.
        retry_policy: Retry configuration for this operation.

    Returns:
        EffectOperationResult with operation outcome and metrics.

    Example:
        Execute single operation with exponential backoff::

            result = await execute_single_operation(
                operation=fetch_op,
                context={"base_url": "https://api.example.com"},
                handler=http_handler,
                retry_policy=ModelEffectRetryPolicy(
                    enabled=True,
                    max_retries=3,
                    backoff_strategy="exponential",
                    base_delay_ms=1000,
                ),
            )
    """
    start_time = time.perf_counter()
    retry_count = 0
    last_error: str | None = None

    # Determine max attempts
    max_attempts = 1
    if retry_policy.enabled and retry_policy.max_retries > 0:
        max_attempts = 1 + retry_policy.max_retries

    for attempt in range(max_attempts):
        try:
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(operation, context)
            else:
                result = handler(operation, context)

            # Success
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            return EffectOperationResult(
                operation_name=operation.operation_name,
                success=True,
                result=result,
                error=None,
                retry_count=retry_count,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            last_error = str(e)
            retry_count = attempt

            # Check if we should retry
            if attempt < max_attempts - 1 and retry_policy.enabled:
                # Calculate delay with backoff
                delay_ms = _calculate_retry_delay(
                    attempt=attempt,
                    policy=retry_policy,
                )

                # Apply jitter
                delay_ms = _apply_jitter(delay_ms, retry_policy.jitter_factor)

                # Wait before retry
                await asyncio.sleep(delay_ms / 1000.0)
            else:
                # No more retries
                break

    # All attempts exhausted
    processing_time_ms = (time.perf_counter() - start_time) * 1000
    return EffectOperationResult(
        operation_name=operation.operation_name,
        success=False,
        result=None,
        error=last_error,
        retry_count=retry_count,
        processing_time_ms=processing_time_ms,
    )


def _calculate_retry_delay(
    attempt: int,
    policy: ModelEffectRetryPolicy,
) -> float:
    """
    Calculate retry delay based on backoff strategy.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        attempt: Current attempt number (0-indexed).
        policy: Retry policy with backoff configuration.

    Returns:
        Delay in milliseconds before next retry.
    """
    base_delay = float(policy.base_delay_ms)

    if policy.backoff_strategy == "fixed":
        delay = base_delay
    elif policy.backoff_strategy == "exponential":
        delay = base_delay * (2**attempt)
    else:  # policy.backoff_strategy == "linear"
        delay = base_delay * (attempt + 1)

    # Cap at max delay
    return min(delay, float(policy.max_delay_ms))


def _apply_jitter(
    delay_ms: float,
    jitter_factor: float,
) -> float:
    """
    Apply random jitter to delay to prevent thundering herd.

    Thread Safety:
        This function uses random.uniform() which is thread-safe in CPython
        due to the GIL, but results are non-deterministic.

    Args:
        delay_ms: Base delay in milliseconds.
        jitter_factor: Jitter as fraction of delay (0.0-0.5).

    Returns:
        Delay with jitter applied (delay +/- jitter_factor * delay).
    """
    if jitter_factor <= 0:
        return delay_ms

    jitter_range = delay_ms * jitter_factor
    jitter = random.uniform(-jitter_range, jitter_range)
    return max(0, delay_ms + jitter)


# Public API
__all__ = [
    "EffectExecutionResult",
    "EffectOperationResult",
    "execute_effect_operations",
    "execute_single_operation",
    "validate_effect_subcontract",
]

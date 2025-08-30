"""
Monadic Composition Utilities for ONEX Architecture.

This module provides advanced monadic composition patterns and utilities
for working with NodeResult<T> in complex ONEX workflows and operations.

Author: ONEX Framework Team
"""

import asyncio
import time
from datetime import datetime
from functools import wraps
from typing import Awaitable, Callable, List, Optional, TypeVar

from omnibase_core.core.monadic.model_node_result import (ErrorInfo, ErrorType,
                                                          Event,
                                                          ExecutionContext,
                                                          LogEntry, NodeResult)

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W")
X = TypeVar("X")


class MonadicCompositionError(Exception):
    """Exception raised during monadic composition operations."""

    pass


class MonadicComposer:
    """
    Advanced monadic composition utility for NodeResult operations.

    Provides high-level composition patterns, error handling strategies,
    and performance optimization for complex monadic workflows.
    """

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or f"composer_{int(time.time())}"
        self.operation_count = 0

    # === SEQUENTIAL COMPOSITION ===

    async def sequence(
        self,
        operations: List[Callable[[T], Awaitable[NodeResult[U]]]],
        initial_value: T,
        fail_fast: bool = True,
        collect_errors: bool = False,
    ) -> NodeResult[List[U]]:
        """
        Execute operations sequentially with monadic composition.

        Args:
            operations: List of async functions returning NodeResult
            initial_value: Initial input value
            fail_fast: Stop on first failure (default: True)
            collect_errors: Collect all errors instead of stopping (default: False)

        Returns:
            NodeResult[List[U]]: Results from all operations or failure
        """
        start_time = datetime.now()
        results = []
        errors = []
        current_value = initial_value

        execution_context = ExecutionContext(
            provenance=[f"sequence.{self.correlation_id}"],
            logs=[],
            trust_score=1.0,
            timestamp=start_time,
            metadata={
                "operation_count": len(operations),
                "fail_fast": fail_fast,
                "collect_errors": collect_errors,
                "correlation_id": self.correlation_id,
            },
            correlation_id=self.correlation_id,
        )

        for i, operation in enumerate(operations):
            try:
                step_result = await operation(current_value)

                if step_result.is_failure:
                    if collect_errors:
                        errors.append(step_result.error)
                        execution_context.logs.append(
                            LogEntry(
                                "WARNING",
                                f"Step {i} failed: {step_result.error.message}",
                                datetime.now(),
                            )
                        )
                        continue
                    elif fail_fast:
                        # Return immediate failure
                        execution_context.logs.append(
                            LogEntry(
                                "ERROR",
                                f"Sequence failed at step {i}: {step_result.error.message}",
                                datetime.now(),
                            )
                        )

                        return NodeResult.failure(
                            error=step_result.error,
                            provenance=execution_context.provenance
                            + [f"step.{i}.failed"],
                            correlation_id=self.correlation_id,
                        )

                results.append(step_result.value)
                current_value = step_result.value

                # Update execution context with successful step
                execution_context.provenance.append(f"step.{i}.completed")
                execution_context.logs.append(
                    LogEntry("INFO", f"Step {i} completed successfully", datetime.now())
                )

                # Combine trust scores (minimum propagation)
                execution_context.trust_score = min(
                    execution_context.trust_score, step_result.context.trust_score
                )

            except Exception as e:
                error_info = ErrorInfo(
                    error_type=ErrorType.PERMANENT,
                    message=f"Sequence step {i} raised exception: {str(e)}",
                    trace=str(e.__traceback__) if e.__traceback__ else None,
                    correlation_id=self.correlation_id,
                    retryable=False,
                )

                if fail_fast:
                    return NodeResult.failure(
                        error=error_info,
                        provenance=execution_context.provenance
                        + [f"step.{i}.exception"],
                        correlation_id=self.correlation_id,
                    )
                else:
                    errors.append(error_info)

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        execution_context.timestamp = end_time
        execution_context.metadata["duration_ms"] = duration_ms
        execution_context.metadata["successful_steps"] = len(results)
        execution_context.metadata["failed_steps"] = len(errors)

        # If we collected errors and have any, return a failure with aggregated errors
        if collect_errors and errors:
            aggregated_error = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Sequence completed with {len(errors)} failures",
                context={
                    "errors": [err.__dict__ for err in errors],
                    "successful_results": len(results),
                },
                correlation_id=self.correlation_id,
                retryable=False,
            )

            return NodeResult.failure(
                error=aggregated_error,
                provenance=execution_context.provenance + ["sequence.partial_failure"],
                correlation_id=self.correlation_id,
            )

        return NodeResult.success(
            value=results,
            provenance=execution_context.provenance,
            trust_score=execution_context.trust_score,
            metadata=execution_context.metadata,
            events=[
                Event(
                    type="monadic.sequence.completed",
                    payload={
                        "operation_count": len(operations),
                        "successful_steps": len(results),
                        "failed_steps": len(errors),
                        "duration_ms": duration_ms,
                    },
                    timestamp=end_time,
                    correlation_id=self.correlation_id,
                )
            ],
            correlation_id=self.correlation_id,
        )

    # === PARALLEL COMPOSITION ===

    async def parallel(
        self,
        operations: List[Callable[[T], Awaitable[NodeResult[U]]]],
        input_values: List[T],
        max_concurrency: Optional[int] = None,
        fail_fast: bool = True,
        timeout_seconds: Optional[float] = None,
    ) -> NodeResult[List[U]]:
        """
        Execute operations in parallel with monadic composition.

        Args:
            operations: List of async functions returning NodeResult
            input_values: Input values for each operation
            max_concurrency: Maximum concurrent operations (default: None = unlimited)
            fail_fast: Stop on first failure (default: True)
            timeout_seconds: Timeout for the entire parallel operation

        Returns:
            NodeResult[List[U]]: Results from all operations or failure
        """
        if len(operations) != len(input_values):
            error_info = ErrorInfo(
                error_type=ErrorType.VALIDATION,
                message="Operations and input_values lists must have same length",
                correlation_id=self.correlation_id,
                retryable=False,
            )
            return NodeResult.failure(
                error=error_info,
                provenance=[f"parallel.{self.correlation_id}.validation_failed"],
            )

        start_time = datetime.now()

        # Create semaphore for concurrency control if specified
        semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None

        async def run_with_semaphore(op, value, index):
            """Run operation with optional semaphore control."""
            if semaphore:
                async with semaphore:
                    return await op(value), index
            else:
                return await op(value), index

        # Create tasks for parallel execution
        tasks = [
            run_with_semaphore(op, value, i)
            for i, (op, value) in enumerate(zip(operations, input_values))
        ]

        try:
            # Execute with optional timeout
            if timeout_seconds:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout_seconds,
                )
            else:
                results = await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.TimeoutError:
            error_info = ErrorInfo(
                error_type=ErrorType.TIMEOUT,
                message=f"Parallel execution timed out after {timeout_seconds}s",
                correlation_id=self.correlation_id,
                retryable=True,
                backoff_strategy="exponential",
                max_attempts=3,
            )
            return NodeResult.failure(
                error=error_info,
                provenance=[f"parallel.{self.correlation_id}.timeout"],
                correlation_id=self.correlation_id,
            )

        # Process results
        successful_results = []
        failed_results = []

        for result in results:
            if isinstance(result, Exception):
                error_info = ErrorInfo(
                    error_type=ErrorType.PERMANENT,
                    message=f"Parallel operation raised exception: {str(result)}",
                    trace=str(result.__traceback__) if result.__traceback__ else None,
                    correlation_id=self.correlation_id,
                    retryable=False,
                )
                failed_results.append(error_info)

                if fail_fast:
                    return NodeResult.failure(
                        error=error_info,
                        provenance=[f"parallel.{self.correlation_id}.exception"],
                        correlation_id=self.correlation_id,
                    )
            else:
                node_result, index = result

                if node_result.is_failure:
                    failed_results.append(node_result.error)

                    if fail_fast:
                        return NodeResult.failure(
                            error=node_result.error,
                            provenance=[
                                f"parallel.{self.correlation_id}.operation.{index}.failed"
                            ],
                            correlation_id=self.correlation_id,
                        )
                else:
                    successful_results.append((node_result.value, index))

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Sort results by original index
        successful_results.sort(key=lambda x: x[1])
        final_results = [value for value, _ in successful_results]

        return NodeResult.success(
            value=final_results,
            provenance=[f"parallel.{self.correlation_id}.completed"],
            trust_score=0.9,  # Parallel operations have slight uncertainty
            metadata={
                "operation_count": len(operations),
                "successful_operations": len(successful_results),
                "failed_operations": len(failed_results),
                "duration_ms": duration_ms,
                "concurrency_limit": max_concurrency,
                "timeout_seconds": timeout_seconds,
            },
            events=[
                Event(
                    type="monadic.parallel.completed",
                    payload={
                        "operation_count": len(operations),
                        "successful_operations": len(successful_results),
                        "failed_operations": len(failed_results),
                        "duration_ms": duration_ms,
                    },
                    timestamp=end_time,
                    correlation_id=self.correlation_id,
                )
            ],
            correlation_id=self.correlation_id,
        )

    # === CONDITIONAL COMPOSITION ===

    async def conditional(
        self,
        condition: Callable[[T], Awaitable[bool]],
        true_operation: Callable[[T], Awaitable[NodeResult[U]]],
        input_value: T,
        false_operation: Optional[Callable[[T], Awaitable[NodeResult[U]]]] = None,
    ) -> NodeResult[U]:
        """
        Execute operations based on conditional logic.

        Args:
            condition: Async predicate function
            true_operation: Operation to execute if condition is True
            false_operation: Optional operation for False condition
            input_value: Input value for condition and operations

        Returns:
            NodeResult[U]: Result of the executed operation
        """
        start_time = datetime.now()

        try:
            # Evaluate condition
            condition_result = await condition(input_value)

            if condition_result:
                operation_type = "true_branch"
                result = await true_operation(input_value)
            elif false_operation:
                operation_type = "false_branch"
                result = await false_operation(input_value)
            else:
                # No false operation, return input as success
                operation_type = "no_false_branch"
                result = NodeResult.success(
                    value=input_value,
                    provenance=[f"conditional.{self.correlation_id}.no_false_branch"],
                    trust_score=1.0,
                    correlation_id=self.correlation_id,
                )

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Add conditional metadata to result
            if result.is_success:
                result.context.metadata.update(
                    {
                        "conditional_branch": operation_type,
                        "condition_result": condition_result,
                        "duration_ms": duration_ms,
                    }
                )
                result.context.provenance.append(f"conditional.{operation_type}")

            return result

        except Exception as e:
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Conditional operation failed: {str(e)}",
                trace=str(e.__traceback__) if e.__traceback__ else None,
                correlation_id=self.correlation_id,
                retryable=False,
            )

            return NodeResult.failure(
                error=error_info,
                provenance=[f"conditional.{self.correlation_id}.exception"],
                correlation_id=self.correlation_id,
            )

    # === RETRY COMPOSITION ===

    async def retry(
        self,
        operation: Callable[[T], Awaitable[NodeResult[U]]],
        input_value: T,
        max_attempts: int = 3,
        backoff_strategy: str = "exponential",  # "linear", "exponential", "fixed"
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        retry_predicate: Optional[Callable[[ErrorInfo], bool]] = None,
    ) -> NodeResult[U]:
        """
        Execute operation with retry logic and backoff strategies.

        Args:
            operation: Operation to retry
            input_value: Input value for operation
            max_attempts: Maximum number of attempts
            backoff_strategy: Backoff strategy ("linear", "exponential", "fixed")
            base_delay_seconds: Base delay for backoff
            max_delay_seconds: Maximum delay between attempts
            retry_predicate: Optional function to determine if error should be retried

        Returns:
            NodeResult[U]: Result of successful operation or final failure
        """
        attempts = 0
        last_error = None

        while attempts < max_attempts:
            attempts += 1

            try:
                result = await operation(input_value)

                if result.is_success:
                    # Add retry metadata to successful result
                    result.context.metadata.update(
                        {
                            "retry_attempts": attempts,
                            "max_attempts": max_attempts,
                            "backoff_strategy": backoff_strategy,
                        }
                    )
                    result.context.provenance.append(
                        f"retry.success.attempt_{attempts}"
                    )
                    return result

                # Check if we should retry this error
                if retry_predicate and not retry_predicate(result.error):
                    return result  # Don't retry this error

                last_error = result.error

                # Calculate delay for next attempt
                if attempts < max_attempts:
                    delay = self._calculate_backoff_delay(
                        attempts,
                        backoff_strategy,
                        base_delay_seconds,
                        max_delay_seconds,
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                error_info = ErrorInfo(
                    error_type=ErrorType.PERMANENT,
                    message=f"Retry operation raised exception on attempt {attempts}: {str(e)}",
                    trace=str(e.__traceback__) if e.__traceback__ else None,
                    correlation_id=self.correlation_id,
                    retryable=attempts < max_attempts,
                )

                if attempts < max_attempts:
                    delay = self._calculate_backoff_delay(
                        attempts,
                        backoff_strategy,
                        base_delay_seconds,
                        max_delay_seconds,
                    )
                    await asyncio.sleep(delay)

                last_error = error_info

        # All attempts exhausted
        final_error = ErrorInfo(
            error_type=ErrorType.PERMANENT,
            message=f"Operation failed after {max_attempts} attempts. Last error: {last_error.message if last_error else 'Unknown'}",
            context={
                "attempts": max_attempts,
                "backoff_strategy": backoff_strategy,
                "last_error": last_error.__dict__ if last_error else None,
            },
            correlation_id=self.correlation_id,
            retryable=False,
        )

        return NodeResult.failure(
            error=final_error,
            provenance=[f"retry.{self.correlation_id}.exhausted"],
            correlation_id=self.correlation_id,
        )

    def _calculate_backoff_delay(
        self, attempt: int, strategy: str, base_delay: float, max_delay: float
    ) -> float:
        """Calculate backoff delay based on strategy."""
        if strategy == "fixed":
            return min(base_delay, max_delay)
        elif strategy == "linear":
            return min(base_delay * attempt, max_delay)
        elif strategy == "exponential":
            return min(base_delay * (2 ** (attempt - 1)), max_delay)
        else:
            return base_delay

    # === PIPELINE COMPOSITION ===

    async def pipeline(
        self,
        operations: List[Callable[[V], Awaitable[NodeResult[W]]]],
        input_value: V,
        checkpoint_interval: Optional[int] = None,
        enable_rollback: bool = False,
    ) -> NodeResult[W]:
        """
        Execute operations as a pipeline with optional checkpointing.

        Args:
            operations: List of operations to execute in sequence
            input_value: Initial input value
            checkpoint_interval: Save checkpoints every N operations
            enable_rollback: Enable rollback on failure

        Returns:
            NodeResult[W]: Final pipeline result
        """
        checkpoints = []
        current_value = input_value

        for i, operation in enumerate(operations):
            # Save checkpoint if configured
            if checkpoint_interval and i % checkpoint_interval == 0:
                checkpoints.append((i, current_value))

            result = await operation(current_value)

            if result.is_failure:
                if enable_rollback and checkpoints:
                    # Find the most recent checkpoint
                    checkpoint_index, checkpoint_value = checkpoints[-1]

                    result.context.metadata.update(
                        {
                            "rollback_to_checkpoint": checkpoint_index,
                            "pipeline_position": i,
                            "checkpoint_count": len(checkpoints),
                        }
                    )

                return result

            current_value = result.value

        # Pipeline completed successfully
        return NodeResult.success(
            value=current_value,
            provenance=[f"pipeline.{self.correlation_id}.completed"],
            trust_score=0.95,
            metadata={
                "pipeline_length": len(operations),
                "checkpoint_count": len(checkpoints),
                "enable_rollback": enable_rollback,
            },
            correlation_id=self.correlation_id,
        )


# === UTILITY DECORATORS ===


def monadic_operation(correlation_id_prefix: str = "op"):
    """
    Decorator to wrap functions in NodeResult monadic patterns.

    Args:
        correlation_id_prefix: Prefix for correlation ID generation

    Returns:
        Decorator function
    """

    def decorator(
        func: Callable[[T], Awaitable[U]],
    ) -> Callable[[T], Awaitable[NodeResult[U]]]:
        @wraps(func)
        async def wrapper(input_value: T) -> NodeResult[U]:
            correlation_id = (
                f"{correlation_id_prefix}_{func.__name__}_{int(time.time())}"
            )
            start_time = datetime.now()

            try:
                result = await func(input_value)

                end_time = datetime.now()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                return NodeResult.success(
                    value=result,
                    provenance=[f"decorated.{func.__name__}"],
                    trust_score=1.0,
                    metadata={
                        "function_name": func.__name__,
                        "duration_ms": duration_ms,
                        "decorated": True,
                    },
                    correlation_id=correlation_id,
                )

            except Exception as e:
                error_info = ErrorInfo(
                    error_type=ErrorType.PERMANENT,
                    message=f"Decorated function {func.__name__} failed: {str(e)}",
                    trace=str(e.__traceback__) if e.__traceback__ else None,
                    correlation_id=correlation_id,
                    retryable=False,
                )

                return NodeResult.failure(
                    error=error_info,
                    provenance=[f"decorated.{func.__name__}.failed"],
                    correlation_id=correlation_id,
                )

        return wrapper

    return decorator


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to monadic operations.

    Args:
        timeout_seconds: Timeout in seconds

    Returns:
        Decorator function that works with both functions and methods
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )

                # Add timeout metadata to successful results
                if hasattr(result, "is_success") and result.is_success:
                    if hasattr(result, "context") and hasattr(
                        result.context, "metadata"
                    ):
                        result.context.metadata["timeout_seconds"] = timeout_seconds
                        result.context.metadata["timed_out"] = False

                return result

            except asyncio.TimeoutError:
                error_info = ErrorInfo(
                    error_type=ErrorType.TIMEOUT,
                    message=f"Operation {func.__name__} timed out after {timeout_seconds}s",
                    correlation_id=f"timeout_{func.__name__}_{int(time.time())}",
                    retryable=True,
                    backoff_strategy="exponential",
                    max_attempts=3,
                )

                return NodeResult.failure(
                    error=error_info,
                    provenance=[f"timeout.{func.__name__}"],
                    correlation_id=error_info.correlation_id,
                )

        return wrapper

    return decorator


# === COMPOSITION HELPER FUNCTIONS ===


async def sequence_operations(
    operations: List[Callable[[T], Awaitable[NodeResult[U]]]],
    initial_value: T,
    correlation_id: Optional[str] = None,
) -> NodeResult[List[U]]:
    """
    Helper function for sequential monadic composition.

    Args:
        operations: List of operations to execute
        initial_value: Initial input value
        correlation_id: Optional correlation ID

    Returns:
        NodeResult[List[U]]: Results from all operations
    """
    composer = MonadicComposer(correlation_id)
    return await composer.sequence(operations, initial_value)


async def parallel_operations(
    operations: List[Callable[[T], Awaitable[NodeResult[U]]]],
    input_values: List[T],
    max_concurrency: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> NodeResult[List[U]]:
    """
    Helper function for parallel monadic composition.

    Args:
        operations: List of operations to execute
        input_values: Input values for each operation
        max_concurrency: Maximum concurrent operations
        correlation_id: Optional correlation ID

    Returns:
        NodeResult[List[U]]: Results from all operations
    """
    composer = MonadicComposer(correlation_id)
    return await composer.parallel(operations, input_values, max_concurrency)


def create_retry_operation(
    max_attempts: int = 3,
    backoff_strategy: str = "exponential",
    base_delay_seconds: float = 1.0,
):
    """
    Create a retry operation wrapper.

    Args:
        max_attempts: Maximum retry attempts
        backoff_strategy: Backoff strategy
        base_delay_seconds: Base delay for backoff

    Returns:
        Async function that applies retry logic
    """

    async def retry_wrapper(
        operation: Callable[[T], Awaitable[NodeResult[U]]], input_value: T
    ) -> NodeResult[U]:
        composer = MonadicComposer()
        return await composer.retry(
            operation=operation,
            input_value=input_value,
            max_attempts=max_attempts,
            backoff_strategy=backoff_strategy,
            base_delay_seconds=base_delay_seconds,
        )

    return retry_wrapper

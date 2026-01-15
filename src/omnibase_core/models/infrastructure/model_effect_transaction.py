"""
ModelEffectTransaction - Transaction management for side effect operations.

Provides rollback capabilities and operation tracking for complex side effect
sequences in the ONEX 4-Node Architecture.

"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from omnibase_core.enums.enum_effect_types import EnumTransactionState
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_transaction_operation import (
    ModelTransactionOperation,
    ModelTransactionOperationData,
)

__all__ = ["ModelEffectTransaction"]


class ModelEffectTransaction:
    """
    Transaction management for side effect operations.

    Provides rollback capabilities and operation tracking
    for complex side effect sequences.

    Attributes:
        transaction_id: Unique identifier for this transaction
        state: Current transaction state (PENDING, COMMITTED, ROLLED_BACK, FAILED)
        operations: List of operations performed during this transaction
        rollback_operations: List of (operation_name, rollback_function) tuples
        rollback_failures: List of error messages from failed rollback operations
        rollback_errors: List of structured ModelOnexError objects with full context
        started_at: Timestamp when transaction was created
        committed_at: Timestamp when transaction was committed (None if not committed)

    Rollback Semantics:
        - Rollback failures are logged and returned via structured ModelOnexError objects
        - Partial rollback failures are captured with details of which operations failed
        - Original exception details preserved in ModelOnexError context (operation, type, message)
        - All rollback attempts are made even if some fail (no fail-fast behavior)
    """

    def __init__(self, transaction_id: UUID):
        self.transaction_id = transaction_id
        self.state = EnumTransactionState.PENDING
        self.operations: list[ModelTransactionOperation] = []
        self.rollback_operations: list[tuple[str, Callable[[], object]]] = []
        self.rollback_failures: list[str] = []  # Track which rollbacks failed
        self._rollback_errors: list[ModelOnexError] = []  # Structured error tracking
        self.started_at = datetime.now()
        self.committed_at: datetime | None = None

    def add_operation(
        self,
        operation_name: str,
        operation_data: ModelTransactionOperationData | dict[str, object],
        rollback_func: Callable[[], object] | None = None,
    ) -> None:
        """Add operation to ModelEffectTransaction with optional rollback function."""
        # Convert dict to typed model if needed
        if isinstance(operation_data, dict):
            typed_data = ModelTransactionOperationData.from_dict(operation_data)
        else:
            typed_data = operation_data

        operation = ModelTransactionOperation.create(
            name=operation_name,
            data=typed_data,
            timestamp=datetime.now(),
        )
        self.operations.append(operation)

        if rollback_func:
            self.rollback_operations.append((operation_name, rollback_func))

    async def commit(self) -> None:
        """Commit ModelEffectTransaction - marks as successful."""
        self.state = EnumTransactionState.COMMITTED
        self.committed_at = datetime.now()

    async def rollback(self) -> tuple[bool, list[ModelOnexError]]:
        """
        Rollback all operations in reverse order with explicit failure tracking.

        Returns:
            Tuple of (all_succeeded, failure_list)
            - all_succeeded: True if all rollbacks succeeded, False otherwise
            - failure_list: List of ModelOnexError for failed rollbacks (empty if all succeeded)

        Logging:
            - Each rollback failure logged at ERROR level with full context
            - Successful rollbacks logged at DEBUG level
            - Final rollback summary logged at INFO/ERROR level

        Behavior:
            - Attempts ALL rollbacks even if some fail (no fail-fast)
            - State set to ROLLED_BACK only if all rollbacks succeed, FAILED otherwise
            - Rollback failures captured in rollback_failures field
        """
        failures: list[ModelOnexError] = []

        for idx, (operation_name, rollback_func) in enumerate(
            reversed(self.rollback_operations)
        ):
            try:
                if asyncio.iscoroutinefunction(rollback_func):
                    await rollback_func()
                else:
                    rollback_func()

                emit_log_event(
                    LogLevel.DEBUG,
                    f"Rolled back operation: {operation_name}",
                    {
                        "transaction_id": str(self.transaction_id),
                        "operation": operation_name,
                    },
                )

            except (AttributeError, RuntimeError, ValueError) as e:
                error = ModelOnexError(
                    message=f"Rollback failed for operation: {operation_name} - {e!s}",
                    error_code="ROLLBACK_FAILURE",
                    operation=operation_name,
                    transaction_id=str(self.transaction_id),
                    operation_index=idx,
                    original_error=str(e),
                    original_error_type=type(e).__name__,
                )
                # Use native exception chaining to preserve the original exception
                error.__cause__ = e
                failures.append(error)

                emit_log_event(
                    LogLevel.ERROR,
                    f"Rollback failed for operation {operation_name}: {e!s}",
                    {
                        "transaction_id": str(self.transaction_id),
                        "operation": operation_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        # Store failure messages and structured errors for inspection
        self.rollback_failures = [f.message for f in failures]
        self._rollback_errors = failures

        # Log final summary
        if failures:
            emit_log_event(
                LogLevel.ERROR,
                f"Transaction rollback completed with {len(failures)} failures",
                {
                    "transaction_id": str(self.transaction_id),
                    "total_operations": len(self.rollback_operations),
                    "failures": len(failures),
                    "failure_operations": [
                        f.context.get("operation") for f in failures
                    ],
                },
            )
        else:
            emit_log_event(
                LogLevel.INFO,
                "Transaction rollback completed successfully",
                {
                    "transaction_id": str(self.transaction_id),
                    "total_operations": len(self.rollback_operations),
                },
            )

        # Set final state based on rollback success
        self.state = (
            EnumTransactionState.ROLLED_BACK
            if not failures
            else EnumTransactionState.FAILED
        )

        return (len(failures) == 0, failures)

    @property
    def rollback_errors(self) -> list[ModelOnexError]:
        """
        Expose structured rollback errors for external inspection.

        Returns:
            List of ModelOnexError objects from failed rollback operations
        """
        return self._rollback_errors

"""Transaction model for side effect management with rollback support."""

import asyncio
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_transaction_state import EnumTransactionState
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event

from .model_transaction_operation import (
    ModelTransactionOperation,
    ModelTransactionOperationData,
)


class ModelTransaction:
    """
    Transaction management for side effect operations.

    Provides rollback capabilities and operation tracking
    for complex side effect sequences.
    """

    def __init__(self, transaction_id: UUID):
        self.transaction_id = transaction_id
        self.state = EnumTransactionState.PENDING
        self.operations: list[ModelTransactionOperation] = []
        self.rollback_operations: list[Callable[[], object]] = []
        self.started_at = datetime.now()
        self.committed_at: datetime | None = None

    def add_operation(
        self,
        operation_name: str,
        operation_data: ModelTransactionOperationData | dict[str, object],
        rollback_func: Callable[[], object] | None = None,
    ) -> None:
        """Add operation to transaction with optional rollback function."""
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
            self.rollback_operations.append(rollback_func)

    async def commit(self) -> None:
        """Commit transaction - marks as successful."""
        self.state = EnumTransactionState.COMMITTED
        self.committed_at = datetime.now()

    async def rollback(self) -> None:
        """Rollback transaction - execute all rollback operations."""
        self.state = EnumTransactionState.ROLLED_BACK

        # Store cancellation exception to re-raise after completing all rollback
        # operations, preserving the original exception context and traceback.
        cancelled_error: asyncio.CancelledError | None = None

        # Execute rollback operations in reverse order
        for rollback_func in reversed(self.rollback_operations):
            try:
                if asyncio.iscoroutinefunction(rollback_func):
                    await rollback_func()
                else:
                    rollback_func()
            except asyncio.CancelledError as e:
                # Note cancellation but continue with remaining rollback operations
                # to maintain transaction consistency. Re-raise after all operations.
                cancelled_error = e
                emit_log_event(
                    LogLevel.WARNING,
                    "Rollback cancelled - continuing with remaining operations",
                    {
                        "transaction_id": str(self.transaction_id),
                    },
                )
            except (GeneratorExit, KeyboardInterrupt, SystemExit):
                # Re-raise process signals immediately to honor termination requests.
                # These indicate the process or generator should stop and must always
                # propagate without suppression.
                raise
            except Exception as e:  # cleanup-resilience-ok: rollback must complete
                # Catch all Exception subclasses to ensure all rollback operations
                # are attempted even if one fails. Errors are logged but not re-raised
                # to maximize rollback completion. asyncio.CancelledError is handled
                # separately above and re-raised after all rollback operations complete
                # to honor task cancellation.
                emit_log_event(
                    LogLevel.ERROR,
                    f"Rollback operation failed during cleanup: {e!s}",
                    {
                        "transaction_id": str(self.transaction_id),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        # After all rollback operations complete, honor any pending cancellation
        # by re-raising the original exception to preserve context and traceback.
        if cancelled_error is not None:
            raise cancelled_error

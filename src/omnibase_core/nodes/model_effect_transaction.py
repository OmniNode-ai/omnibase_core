"""
ModelEffectTransaction - Transaction management for side effect operations.

Provides rollback capabilities and operation tracking for complex side effect
sequences in the ONEX 4-Node Architecture.

Author: ONEX Framework Team
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.nodes.enum_effect_types import EnumTransactionState

__all__ = ["ModelEffectTransaction"]


class ModelEffectTransaction:
    """
    Transaction management for side effect operations.

    Provides rollback capabilities and operation tracking
    for complex side effect sequences.
    """

    def __init__(self, transaction_id: UUID):
        self.transaction_id = transaction_id
        self.state = EnumTransactionState.PENDING
        self.operations: list[dict[str, Any]] = []
        self.rollback_operations: list[Callable[..., Any]] = []
        self.started_at = datetime.now()
        self.committed_at: datetime | None = None

    def add_operation(
        self,
        operation_name: str,
        operation_data: dict[str, Any],
        rollback_func: Callable[..., Any] | None = None,
    ) -> None:
        """Add operation to ModelEffectTransaction with optional rollback function."""
        self.operations.append(
            {
                "name": operation_name,
                "data": operation_data,
                "timestamp": datetime.now(),
            },
        )

        if rollback_func:
            self.rollback_operations.append(rollback_func)

    async def commit(self) -> None:
        """Commit ModelEffectTransaction - marks as successful."""
        self.state = EnumTransactionState.COMMITTED
        self.committed_at = datetime.now()

    async def rollback(self) -> None:
        """Rollback ModelEffectTransaction - execute all rollback operations."""
        self.state = EnumTransactionState.ROLLED_BACK

        for rollback_func in reversed(self.rollback_operations):
            try:
                if asyncio.iscoroutinefunction(rollback_func):
                    await rollback_func()
                else:
                    rollback_func()
            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Rollback operation failed: {e!s}",
                    {"transaction_id": str(self.transaction_id), "error": str(e)},
                )

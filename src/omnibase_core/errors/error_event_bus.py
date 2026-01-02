"""
Event Bus Error.

Event bus operation error for Runtime Host operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime_host import RuntimeHostError


class EventBusError(RuntimeHostError):
    """
    Event bus operation errors.

    Raised when event bus operations fail (publish, subscribe, deliver).
    Supports correlation tracking across event-driven workflows.

    Example:
        raise EventBusError(
            "Failed to publish event to topic",
            operation="publish",
            topic="node.events",
            correlation_id=event.correlation_id,
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., topic, event_type, etc.)
    def __init__(
        self,
        message: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize EventBusError with event context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to EVENT_BUS_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name (e.g., "publish", "subscribe")
            **context: Additional structured context (e.g., topic, event_type)
        """
        # Use EVENT_BUS_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.EVENT_BUS_ERROR

        # Call parent with all structured fields
        super().__init__(
            message=message,
            error_code=final_error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            operation=operation,
            **context,
        )


__all__ = ["EventBusError"]

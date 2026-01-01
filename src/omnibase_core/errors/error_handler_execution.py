"""
Handler Execution Error.

Handler-specific execution error for Runtime Host operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime_host import RuntimeHostError


class HandlerExecutionError(RuntimeHostError):
    """
    Handler-specific execution errors.

    Raised when a protocol handler (HTTP, Kafka, Database, etc.) fails to
    execute an operation. Includes handler_type for debugging and metrics.

    Required Fields:
        handler_type: Type of handler that failed (e.g., "HTTP", "Kafka", "Database")

    Example:
        raise HandlerExecutionError(
            "Kafka producer timeout",
            handler_type="Kafka",
            operation="publish_message",
            topic="events",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., topic, retry_count, etc.)
    def __init__(
        self,
        message: str,
        handler_type: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize HandlerExecutionError with handler context.

        Args:
            message: Human-readable error message
            handler_type: Type of handler (e.g., "HTTP", "Kafka", "Database")
            error_code: Optional error code (defaults to HANDLER_EXECUTION_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            **context: Additional structured context
        """
        # Use HANDLER_EXECUTION_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.HANDLER_EXECUTION_ERROR

        # Add handler_type to context
        context["handler_type"] = handler_type

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

        # Store handler_type as attribute for direct access
        self.handler_type = handler_type


__all__ = ["HandlerExecutionError"]

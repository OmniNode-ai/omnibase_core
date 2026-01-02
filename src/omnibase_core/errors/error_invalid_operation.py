"""
Invalid Operation Error.

Invalid state or operation error for Runtime Host operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime_host import RuntimeHostError


class InvalidOperationError(RuntimeHostError):
    """
    Invalid state or operation errors.

    Raised when an operation is attempted in an invalid state or context.
    Examples: deleting an active node, transitioning to invalid state, etc.

    Example:
        raise InvalidOperationError(
            "Cannot delete node while in RUNNING state",
            operation="delete_node",
            node_id="node-123",
            current_state="RUNNING",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., current_state, node_id, etc.)
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
        Initialize InvalidOperationError with operation context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to INVALID_OPERATION)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            **context: Additional structured context
        """
        # Use INVALID_OPERATION as default code
        final_error_code = error_code or EnumCoreErrorCode.INVALID_OPERATION

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


__all__ = ["InvalidOperationError"]

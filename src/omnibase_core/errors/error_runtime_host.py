"""
Runtime Host Error.

Base error class for all Runtime Host operations with structured error handling.

Error Invariants (MVP Requirements):
- All errors MUST include correlation_id for tracking
- Handler errors MUST include handler_type when applicable
- All errors SHOULD include operation when applicable
- Raw stack traces MUST NOT appear in error envelopes
- Structured fields for logging and observability

Design Principles:
- Inherit from ModelOnexError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.error_runtime_host import RuntimeHostError

    raise RuntimeHostError(
        "Node initialization failed",
        operation="initialize",
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class RuntimeHostError(ModelOnexError):
    """
    Base error for Runtime Host operations.

    All runtime host errors inherit from this class to ensure consistent
    error handling, correlation tracking, and structured logging.

    Attributes:
        message: Human-readable error message
        error_code: Optional error code (defaults to RUNTIME_ERROR)
        correlation_id: UUID for tracking across system (auto-generated if not provided)
        operation: Optional operation name that failed
        **context: Additional structured context

    Example:
        raise RuntimeHostError(
            "Node initialization failed",
            operation="initialize_node",
            node_id="node-123",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., node_id, topic, etc.)
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
        Initialize RuntimeHostError with structured context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to RUNTIME_ERROR if None)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            **context: Additional structured context
        """
        # Use RUNTIME_ERROR as default code if not specified
        final_error_code = error_code or EnumCoreErrorCode.RUNTIME_ERROR

        # Add operation to context if provided
        if operation is not None:
            context["operation"] = operation

        # Call parent with all structured fields
        super().__init__(
            message=message,
            error_code=final_error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            **context,
        )

        # Store operation as attribute for direct access
        self.operation = operation


__all__ = ["RuntimeHostError"]

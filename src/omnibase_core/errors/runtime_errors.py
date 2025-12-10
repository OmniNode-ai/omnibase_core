"""
Runtime Host Error Hierarchy ().

Minimal MVP error classes for Runtime Host operations with structured error handling.

MVP Classes:
- RuntimeHostError: Base error for all runtime host operations
- HandlerExecutionError: Handler-specific execution errors
- EventBusError: Event bus operation errors
- InvalidOperationError: Invalid state or operation errors
- ContractValidationError: Contract/schema validation errors

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
    from omnibase_core.errors.runtime_errors import (
        RuntimeHostError,
        HandlerExecutionError,
        EventBusError,
    )

    # Base runtime error
    raise RuntimeHostError(
        "Node initialization failed",
        operation="initialize",
    )

    # Handler-specific error
    raise HandlerExecutionError(
        "Kafka connection timeout",
        handler_type="Kafka",
        operation="publish_message",
    )

    # Event bus error with correlation tracking
    raise EventBusError(
        "Failed to deliver event",
        operation="publish",
        correlation_id=corr_id,
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


class ContractValidationError(RuntimeHostError):
    """
    Contract/schema validation errors.

    Raised when contract or schema validation fails during node registration,
    configuration loading, or runtime validation.

    Example:
        raise ContractValidationError(
            "Missing required field 'handler_type'",
            operation="validate_contract",
            field="handler_type",
            expected_type="string",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., field, expected_type, etc.)
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
        Initialize ContractValidationError with validation context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to CONTRACT_VALIDATION_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name (e.g., "validate_schema")
            **context: Additional structured context (e.g., field, expected_type)
        """
        # Use CONTRACT_VALIDATION_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

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


__all__ = [
    "ContractValidationError",
    "EventBusError",
    "HandlerExecutionError",
    "InvalidOperationError",
    "RuntimeHostError",
]

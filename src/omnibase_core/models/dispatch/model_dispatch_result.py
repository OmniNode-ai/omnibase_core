"""
Dispatch Result Model.

Represents the result of a dispatch operation, including status, timing metrics,
and any outputs produced by the handler. Used for observability, debugging,
and result propagation in the dispatch engine.

Design Pattern:
    ModelDispatchResult is a pure data model that captures the complete outcome
    of a dispatch operation:
    - Status (success, error, timeout, etc.)
    - Timing metrics (duration, timestamps)
    - Handler outputs (for successful dispatches)
    - Error information (for failed dispatches)
    - Tracing context (correlation IDs, trace IDs)

    This model is produced by the dispatch engine after each dispatch operation
    and can be used for logging, metrics collection, and error handling.

Thread Safety:
    ModelDispatchResult is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.dispatch import ModelDispatchResult, EnumDispatchStatus
    >>> from uuid import uuid4
    >>> from datetime import datetime, UTC
    >>>
    >>> # Create a successful dispatch result
    >>> result = ModelDispatchResult(
    ...     dispatch_id=uuid4(),
    ...     status=EnumDispatchStatus.SUCCESS,
    ...     route_id="user-events-route",
    ...     handler_id="user-event-handler",
    ...     topic="dev.user.events.v1",
    ...     message_type="UserCreatedEvent",
    ...     duration_ms=45.2,
    ...     outputs=["dev.notification.commands.v1"],
    ... )
    >>>
    >>> result.is_successful()
    True

See Also:
    omnibase_core.models.dispatch.ModelDispatchRoute: Routing rule model
    omnibase_core.models.dispatch.EnumDispatchStatus: Dispatch status enum
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.services.model_error_details import ModelErrorDetails


class ModelDispatchResult(BaseModel):
    """
    Result of a dispatch operation.

    Captures the complete outcome of routing a message to a handler,
    including status, timing, outputs, and error information.

    Attributes:
        dispatch_id: Unique identifier for this dispatch operation.
        status: The outcome status of the dispatch operation.
        route_id: Identifier of the route that was matched (if any).
        handler_id: Identifier of the handler that was invoked (if any).
        topic: The topic the message was dispatched to.
        message_category: The category of the dispatched message.
        message_type: The specific type of the message (if known).
        duration_ms: Time taken for the dispatch operation in milliseconds.
        started_at: Timestamp when the dispatch started.
        completed_at: Timestamp when the dispatch completed.
        outputs: List of topics where handler outputs were published.
        output_count: Number of outputs produced by the handler.
        error_message: Error message if the dispatch failed.
        error_code: Error code if the dispatch failed.
        error_details: Additional error details for debugging.
        retry_count: Number of times this dispatch was retried.
        correlation_id: Correlation ID from the original message.
        trace_id: Distributed trace ID for observability.
        span_id: Trace span ID for this dispatch operation.
        metadata: Optional additional metadata about the dispatch.

    Example:
        >>> result = ModelDispatchResult(
        ...     dispatch_id=uuid4(),
        ...     status=EnumDispatchStatus.HANDLER_ERROR,
        ...     route_id="order-route",
        ...     handler_id="order-handler",
        ...     topic="dev.order.commands.v1",
        ...     message_category=EnumMessageCategory.COMMAND,
        ...     error_message="Database connection failed",
        ...     error_code="DB_CONNECTION_ERROR",
        ... )
        >>> result.is_error()
        True
        >>> result.requires_retry()
        False
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Dispatch Identity ----
    dispatch_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this dispatch operation.",
    )

    # ---- Status ----
    status: EnumDispatchStatus = Field(
        ...,
        description="The outcome status of the dispatch operation.",
    )

    # ---- Route and Handler Info ----
    route_id: str | None = Field(
        default=None,
        description="Identifier of the route that was matched (if any).",
    )
    handler_id: str | None = Field(
        default=None,
        description="Identifier of the handler that was invoked (if any).",
    )

    # ---- Message Info ----
    topic: str = Field(
        ...,
        description="The topic the message was dispatched to.",
        min_length=1,
    )
    message_category: EnumMessageCategory | None = Field(
        default=None,
        description="The category of the dispatched message.",
    )
    message_type: str | None = Field(
        default=None,
        description="The specific type of the message (if known).",
    )

    # ---- Timing Metrics ----
    duration_ms: float | None = Field(
        default=None,
        description="Time taken for the dispatch operation in milliseconds.",
        ge=0,
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the dispatch started (UTC).",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the dispatch completed (UTC).",
    )

    # ---- Handler Outputs ----
    outputs: list[str] | None = Field(
        default=None,
        description="List of topics where handler outputs were published.",
    )
    output_count: int = Field(
        default=0,
        description="Number of outputs produced by the handler.",
        ge=0,
    )

    # ---- Error Information ----
    error_message: str | None = Field(
        default=None,
        description="Error message if the dispatch failed.",
    )
    error_code: str | None = Field(
        default=None,
        description="Error code if the dispatch failed.",
    )
    error_details: ModelErrorDetails[Any] | None = Field(
        default=None,
        description="Additional error details for debugging.",
    )

    # ---- Retry Information ----
    retry_count: int = Field(
        default=0,
        description="Number of times this dispatch was retried.",
        ge=0,
    )

    # ---- Tracing Context ----
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID from the original message.",
    )
    trace_id: UUID | None = Field(
        default=None,
        description="Distributed trace ID for observability.",
    )
    span_id: UUID | None = Field(
        default=None,
        description="Trace span ID for this dispatch operation.",
    )

    # ---- Optional Metadata ----
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Optional additional metadata about the dispatch.",
    )

    def is_successful(self) -> bool:
        """
        Check if this dispatch was successful.

        Returns:
            True if status is SUCCESS, False otherwise

        Example:
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.SUCCESS,
            ...     topic="test.events",
            ... )
            >>> result.is_successful()
            True
        """
        return self.status.is_successful()

    def is_error(self) -> bool:
        """
        Check if this dispatch resulted in an error.

        Returns:
            True if the status represents an error condition, False otherwise

        Example:
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.HANDLER_ERROR,
            ...     topic="test.events",
            ...     error_message="Handler failed",
            ... )
            >>> result.is_error()
            True
        """
        return self.status.is_error()

    def requires_retry(self) -> bool:
        """
        Check if this dispatch should be retried.

        Returns:
            True if the status indicates a retriable failure, False otherwise

        Example:
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.TIMEOUT,
            ...     topic="test.events",
            ... )
            >>> result.requires_retry()
            True
        """
        return self.status.requires_retry()

    def is_terminal(self) -> bool:
        """
        Check if this dispatch is in a terminal state.

        Returns:
            True if the dispatch has completed (success or failure), False otherwise
        """
        return self.status.is_terminal()

    def with_error(
        self,
        status: EnumDispatchStatus,
        message: str,
        code: str | None = None,
        details: ModelErrorDetails[Any] | None = None,
    ) -> "ModelDispatchResult":
        """
        Create a new result with error information.

        Args:
            status: The error status
            message: Error message
            code: Optional error code
            details: Optional error details

        Returns:
            New ModelDispatchResult with error information

        Example:
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.ROUTED,
            ...     topic="test.events",
            ... )
            >>> error_result = result.with_error(
            ...     EnumDispatchStatus.HANDLER_ERROR,
            ...     "Handler failed",
            ...     code="HANDLER_EXCEPTION",
            ... )
        """
        return self.model_copy(
            update={
                "status": status,
                "error_message": message,
                "error_code": code,
                "error_details": details,
                "completed_at": datetime.now(UTC),
            }
        )

    def with_success(
        self,
        outputs: list[str] | None = None,
        output_count: int | None = None,
    ) -> "ModelDispatchResult":
        """
        Create a new result marked as successful.

        Args:
            outputs: Optional list of output topics
            output_count: Optional count of outputs (defaults to len(outputs) if outputs provided, else 0)

        Returns:
            New ModelDispatchResult marked as SUCCESS

        Example:
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.ROUTED,
            ...     topic="test.events",
            ... )
            >>> success_result = result.with_success(
            ...     outputs=["output.topic.v1"],
            ...     output_count=1,
            ... )
        """
        # If output_count explicitly provided, use it; otherwise derive from outputs
        if output_count is not None:
            count = output_count
        elif outputs is not None:
            count = len(outputs)
        else:
            count = 0

        return self.model_copy(
            update={
                "status": EnumDispatchStatus.SUCCESS,
                "outputs": outputs,
                "output_count": count,
                "completed_at": datetime.now(UTC),
            }
        )

    def with_duration(self, duration_ms: float) -> "ModelDispatchResult":
        """
        Create a new result with duration set.

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            New ModelDispatchResult with duration set
        """
        return self.model_copy(
            update={
                "duration_ms": duration_ms,
                "completed_at": datetime.now(UTC),
            }
        )


__all__ = ["ModelDispatchResult"]

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""
Dispatch Result Model (OMN-12546 S-1b promotion).

Represents the result of a dispatch operation, including status, timing metrics,
and any outputs produced by the dispatcher. Used for observability, debugging,
and result propagation in the dispatch engine.

Design Pattern:
    ModelDispatchResult is a pure data model that captures the complete outcome
    of a dispatch operation:
    - Status (success, error, timeout, etc.)
    - Timing metrics (duration, timestamps)
    - Dispatcher outputs (for successful dispatches)
    - Error information (for failed dispatches)
    - Tracing context (correlation IDs, trace IDs)

Thread Safety:
    ModelDispatchResult is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

JsonType Recursion Fix (OMN-1274):
    The ``error_details`` field uses ``dict[str, object]`` instead of the
    recursive ``JsonType`` type alias to avoid Pydantic 2.x eager-expansion
    ``RecursionError`` on nested type aliases.

Example:
    >>> from omnibase_core.models.dispatch import (
    ...     ModelDispatchResult,
    ...     ModelDispatchOutputs,
    ... )
    >>> from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
    >>> from uuid import uuid4
    >>> from datetime import datetime, UTC
    >>>
    >>> # Create a successful dispatch result
    >>> result = ModelDispatchResult(
    ...     dispatch_id=uuid4(),
    ...     status=EnumDispatchStatus.SUCCESS,
    ...     route_id="user-events-route",
    ...     dispatcher_id="user-event-dispatcher",
    ...     topic="dev.user.events.v1",
    ...     message_type="UserCreatedEvent",
    ...     duration_ms=45.2,
    ...     started_at=datetime.now(UTC),
    ...     outputs=ModelDispatchOutputs(topics=["dev.notification.commands.v1"]),
    ... )
    >>>
    >>> result.is_successful()
    True

See Also:
    omnibase_core.models.dispatch.ModelDispatchRoute: Routing rule model
    omnibase_core.enums.enum_dispatch_status.EnumDispatchStatus: Dispatch status enum
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.dispatch.model_dispatch_metadata import ModelDispatchMetadata
from omnibase_core.models.dispatch.model_dispatch_outputs import ModelDispatchOutputs
from omnibase_core.models.projectors.model_projection_intent import (
    ModelProjectionIntent,
)
from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelDispatchResult(BaseModel):
    """
    Result of a dispatch operation.

    Captures the complete outcome of routing a message to a dispatcher,
    including status, timing, outputs, and error information.

    Attributes:
        dispatch_id: Unique identifier for this dispatch operation.
        status: The outcome status of the dispatch operation.
        route_id: Identifier of the route that was matched (if any).
        dispatcher_id: Identifier of the dispatcher that was invoked (if any).
        topic: The topic the message was dispatched to.
        message_category: The category of the dispatched message.
        message_type: The specific type of the message (if known).
        duration_ms: Time taken for the dispatch operation in milliseconds.
        started_at: Timestamp when the dispatch started (must be explicitly provided).
        completed_at: Timestamp when the dispatch completed.
        outputs: Validated output topics where dispatcher outputs were published.
        output_count: Number of outputs produced by the dispatcher.
        output_events: List of output events produced by the dispatcher.
        output_intents: Intents produced by the handler for effect layer execution.
        projection_intents: Projection intents emitted by the reducer.
        dlq_topic: Target DLQ topic for unroutable messages (if determinable).
        error_message: Error message if the dispatch failed.
        error_code: Error code if the dispatch failed (typed EnumCoreErrorCode).
        error_details: Additional JSON-serializable error details for debugging.
        retry_count: Number of times this dispatch was retried.
        correlation_id: Correlation ID from the original message.
        trace_id: Distributed trace ID for observability.
        span_id: Trace span ID for this dispatch operation.
        metadata: Optional additional metadata about the dispatch.

    Example:
        >>> from datetime import datetime, UTC
        >>> result = ModelDispatchResult(
        ...     dispatch_id=uuid4(),
        ...     status=EnumDispatchStatus.HANDLER_ERROR,
        ...     route_id="order-route",
        ...     dispatcher_id="order-dispatcher",
        ...     topic="dev.order.commands.v1",
        ...     message_category=EnumMessageCategory.COMMAND,
        ...     started_at=datetime.now(UTC),
        ...     error_message="Database connection failed",
        ...     error_code=EnumCoreErrorCode.DATABASE_CONNECTION_ERROR,
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

    # ---- Route and Dispatcher Info ----
    route_id: str | None = Field(
        default=None,
        description="Identifier of the route that was matched (if any).",
    )
    dispatcher_id: str | None = Field(
        default=None,
        description="Identifier of the dispatcher that was invoked (if any).",
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
    # Timestamps - MUST be explicitly injected (no default_factory for testability)
    started_at: datetime = Field(
        ...,
        description="Timestamp when the dispatch started (UTC, must be explicitly provided).",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the dispatch completed (UTC).",
    )

    # ---- Dispatcher Outputs ----
    outputs: ModelDispatchOutputs | None = Field(
        default=None,
        description="Validated output topics where dispatcher outputs were published.",
    )
    output_count: int = Field(
        default=0,
        description="Number of outputs produced by the dispatcher.",
        ge=0,
    )
    output_events: list[BaseModel] = Field(
        default_factory=list,
        description=(
            "List of output events produced by the dispatcher that need to be "
            "published to output_topic. These are raw Pydantic models that will "
            "be wrapped in ModelEventEnvelope by the kernel before publishing."
        ),
    )
    output_intents: tuple[ModelIntent, ...] = Field(
        default_factory=tuple,
        description=(
            "Intents produced by the handler for effect layer execution. "
            "These are routed by IntentExecutor after dispatch."
        ),
    )
    projection_intents: tuple[ModelProjectionIntent, ...] = Field(
        default_factory=tuple,
        description=(
            "Projection intents emitted by the reducer (OMN-2509 / OMN-2510). "
            "The runtime executes NodeProjectionEffect synchronously for each "
            "intent before publishing any Kafka messages, ensuring projection "
            "persistence precedes event emission (ordering guarantee)."
        ),
    )

    # ---- DLQ Routing ----
    dlq_topic: str | None = Field(
        default=None,
        description=(
            "Target DLQ topic for unroutable messages. Set when status is "
            "NO_DISPATCHER and a DLQ topic can be derived from the event_type "
            "domain prefix or original topic category. Callers should publish "
            "the original message to this topic for later analysis or retry."
        ),
    )

    # ---- Error Information ----
    error_message: str | None = Field(
        default=None,
        description="Error message if the dispatch failed.",
    )
    error_code: EnumCoreErrorCode | None = Field(
        default=None,
        description="Error code if the dispatch failed (typed, no silent str widening).",
    )
    error_details: dict[str, object] = Field(
        default_factory=dict,
        description="Additional JSON-serializable error details for debugging.",
    )

    # ---- Retry Information ----
    retry_count: int = Field(
        default=0,
        description="Number of times this dispatch was retried.",
        ge=0,
    )

    # ---- Tracing Context ----
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation ID from the original message (auto-generated if not provided).",
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
    metadata: ModelDispatchMetadata | None = Field(
        default=None,
        description="Optional additional metadata about the dispatch.",
    )

    def is_successful(self) -> bool:
        """
        Check if this dispatch was successful.

        Returns:
            True if status is SUCCESS, False otherwise

        Example:
            >>> from datetime import datetime, UTC
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.SUCCESS,
            ...     topic="test.events",
            ...     started_at=datetime.now(UTC),
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
            >>> from datetime import datetime, UTC
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.HANDLER_ERROR,
            ...     topic="test.events",
            ...     started_at=datetime.now(UTC),
            ...     error_message="Dispatcher failed",
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
            >>> from datetime import datetime, UTC
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.TIMEOUT,
            ...     topic="test.events",
            ...     started_at=datetime.now(UTC),
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
        code: EnumCoreErrorCode | None = None,
        details: dict[str, object] | None = None,
    ) -> "ModelDispatchResult":
        """
        Create a new result with error information.

        Args:
            status: The error status
            message: Error message
            code: Optional error code (EnumCoreErrorCode)
            details: Optional JSON-serializable error details

        Returns:
            New ModelDispatchResult with error information

        Example:
            >>> from datetime import datetime, UTC
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.ROUTED,
            ...     topic="test.events",
            ...     started_at=datetime.now(UTC),
            ... )
            >>> error_result = result.with_error(
            ...     EnumDispatchStatus.HANDLER_ERROR,
            ...     "Dispatcher failed",
            ...     code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            ... )
        """
        return self.model_copy(
            update={
                "status": status,
                "error_message": message,
                "error_code": code,
                "error_details": details if details is not None else {},
                "completed_at": datetime.now(UTC),
            }
        )

    def with_success(
        self,
        outputs: ModelDispatchOutputs | None = None,
        output_count: int | None = None,
    ) -> "ModelDispatchResult":
        """
        Create a new result marked as successful.

        Args:
            outputs: Optional ModelDispatchOutputs with validated output topics
            output_count: Optional count of outputs (defaults to len(outputs))

        Returns:
            New ModelDispatchResult marked as SUCCESS

        Example:
            >>> from datetime import datetime, UTC
            >>> result = ModelDispatchResult(
            ...     dispatch_id=uuid4(),
            ...     status=EnumDispatchStatus.ROUTED,
            ...     topic="test.events",
            ...     started_at=datetime.now(UTC),
            ... )
            >>> success_result = result.with_success(
            ...     outputs=ModelDispatchOutputs(topics=["output.topic.v1"]),
            ...     output_count=1,
            ... )
        """
        resolved_outputs: ModelDispatchOutputs = (
            outputs if outputs is not None else ModelDispatchOutputs()
        )
        count = output_count if output_count is not None else len(resolved_outputs)
        return self.model_copy(
            update={
                "status": EnumDispatchStatus.SUCCESS,
                "outputs": resolved_outputs,
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

"""
Reducer handler context - deliberately excludes time injection.

This module provides ModelReducerContext, the execution context passed to
reducer handlers. Unlike other context models (e.g., ModelComputeContext),
this model deliberately omits any time-related fields to enforce reducer
purity.

Thread Safety:
    ModelReducerContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

Design Rationale:
    Reducers are pure functions that must produce deterministic output based
    solely on their input data. Including wall-clock time would violate this
    invariant and break replay safety, event sourcing, and testability.

See Also:
    - omnibase_core.models.reducer.model_reducer_input: Input data model
    - omnibase_core.models.reducer.model_reducer_output: Output model with intents
    - docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md: Reducer node tutorial
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelReducerContext"]


class ModelReducerContext(BaseModel):
    """Context for reducer handler invocations.

    IMPORTANT: This context deliberately does NOT include a `now` field.
    Reducers must be pure functions that produce deterministic output
    based solely on their input data. They must never depend on wall-clock
    time to ensure replay safety and testability.

    If a reducer needs time information, it should be passed as part of
    the event/intent data, not injected as runtime context.

    Attributes:
        correlation_id: Correlation ID for request tracing across services.
            Used to track causality chains through the system.
        envelope_id: Source envelope ID for causality tracking. Links this
            reducer invocation to its triggering event envelope.
        trace_id: Optional distributed tracing ID for observability systems
            (e.g., OpenTelemetry, Jaeger).
        span_id: Optional span ID within the distributed trace.
        partition_id: Optional partition ID for sharded reducers. Used when
            reducers are partitioned by key for parallel processing.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.reducer import ModelReducerContext
        >>>
        >>> context = ModelReducerContext(
        ...     correlation_id=uuid4(),
        ...     envelope_id=uuid4(),
        ...     trace_id="abc123",
        ...     span_id="span456",
        ... )
        >>> # Note: No `now` field - reducers must not access current time
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # NO `now` field - reducers must not access current time

    # Causality tracking
    correlation_id: UUID = Field(
        description="Correlation ID for request tracing across services.",
    )
    envelope_id: UUID = Field(
        description="Source envelope ID for causality tracking.",
    )

    # Optional tracing
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing ID.",
    )
    span_id: str | None = Field(
        default=None,
        description="Span ID within the trace.",
    )

    # Reducer-specific context (no time-dependent fields)
    partition_id: UUID | None = Field(
        default=None,
        description="Partition ID for sharded reducers.",
    )

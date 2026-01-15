"""
Compute handler context - deliberately excludes time injection.

This module provides ModelComputeContext, the execution context passed to
compute handlers. Like ModelReducerContext, this model deliberately omits
any time-related fields to enforce compute purity.

Thread Safety:
    ModelComputeContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

Design Rationale:
    COMPUTE nodes are pure functions that must produce deterministic output
    based solely on their input data. Including wall-clock time would violate
    this invariant and break caching, reproducibility, and testability.

    If a computation needs time information, it should be passed as part of
    the input data, not injected as runtime context.

Distinction from ModelComputeExecutionContext:
    - ModelComputeExecutionContext: Pipeline execution tracking (operation-level)
    - ModelComputeContext: Handler dispatch context (request-level causality)

See Also:
    - omnibase_core.models.compute.model_compute_execution_context: Pipeline context
    - omnibase_core.models.reducer.model_reducer_context: Similar pure context
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelComputeContext"]


class ModelComputeContext(BaseModel):
    """Context for compute handler invocations.

    IMPORTANT: This context deliberately does NOT include a `now` field.
    COMPUTE nodes must be pure functions that produce deterministic output
    based solely on their input data. They must never depend on wall-clock
    time to ensure caching validity, reproducibility, and testability.

    If a computation needs time information, it should be passed as part of
    the input data, not injected as runtime context.

    Attributes:
        correlation_id: Correlation ID for request tracing across services.
            Used to track causality chains through the system.
        envelope_id: Source envelope ID for causality tracking. Links this
            compute invocation to its triggering event envelope.
        dispatch_id: Dispatch operation ID for request tracing. Uniquely identifies
            a single dispatch() call. All handlers in the same dispatch share this ID.
            None for legacy/custom execution paths outside the dispatch engine.
        trace_id: Optional distributed tracing ID (UUID) for observability systems
            (e.g., OpenTelemetry, Jaeger).
        span_id: Optional span ID (UUID) within the distributed trace.
        computation_type: Optional computation type for algorithm tracking
            and routing. Useful for metrics and debugging which transformation
            algorithms are being executed.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.compute import ModelComputeContext
        >>>
        >>> context = ModelComputeContext(
        ...     correlation_id=uuid4(),
        ...     envelope_id=uuid4(),
        ...     trace_id=uuid4(),
        ...     span_id=uuid4(),
        ...     computation_type="transform_json_to_xml",
        ... )
        >>> # Note: No `now` field - compute nodes must not access current time
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # NO `now` field - compute nodes must not access current time

    # Causality tracking
    correlation_id: UUID = Field(
        description="Correlation ID for request tracing across services.",
    )
    envelope_id: UUID = Field(
        description="Source envelope ID for causality tracking.",
    )
    dispatch_id: UUID | None = Field(
        default=None,
        description="Dispatch operation ID for request tracing. Uniquely identifies "
        "a single dispatch() call. All handlers in the same dispatch share this ID. "
        "None for legacy/custom execution paths outside the dispatch engine.",
    )

    # Optional distributed tracing (UUID for consistency with ModelEventEnvelope)
    trace_id: UUID | None = Field(
        default=None,
        description="Distributed tracing ID (e.g., OpenTelemetry trace ID).",
    )
    span_id: UUID | None = Field(
        default=None,
        description="Span ID within the trace (e.g., OpenTelemetry span ID).",
    )

    # Compute-specific context (no time-dependent fields)
    computation_type: str | None = Field(
        default=None,
        description="Computation type for algorithm tracking and routing.",
    )

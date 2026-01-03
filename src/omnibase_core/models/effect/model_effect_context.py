"""Effect handler context with time injection support.

This module provides the execution context model for effect handler invocations.
The context carries time injection for retry timing and metrics calculations,
along with causality tracking identifiers.

Thread Safety:
    ModelEffectContext is immutable (frozen=True) and therefore
    thread-safe for read access after creation.

Key Features:
    - Time injection for deterministic testing of retry logic
    - Causality tracking via correlation_id and envelope_id
    - Optional distributed tracing support (trace_id, span_id)
    - Retry attempt tracking for backoff calculations

Example:
    >>> from uuid import uuid4
    >>> from datetime import UTC, datetime
    >>> from omnibase_core.models.effect import ModelEffectContext
    >>>
    >>> # Create context with injected time for testing
    >>> context = ModelEffectContext(
    ...     correlation_id=uuid4(),
    ...     envelope_id=uuid4(),
    ...     now=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
    ...     retry_attempt=0,
    ... )
    >>>
    >>> # Production usage with auto-generated time
    >>> context = ModelEffectContext(
    ...     correlation_id=uuid4(),
    ...     envelope_id=uuid4(),
    ... )

See Also:
    - omnibase_core.models.effect.model_effect_input: Effect input model
    - omnibase_core.models.effect.model_effect_output: Effect output model
    - omnibase_core.nodes.node_effect: NodeEffect implementation
    - docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md: Effect node tutorial
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectContext"]


class ModelEffectContext(BaseModel):
    """Context for effect handler invocations.

    Provides time injection for retry timing and metrics calculations.
    Effects may use `now` for backoff timing and latency measurements.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Attributes:
        now: Injected current time for retry/metrics calculations. Enables
            deterministic testing by allowing time to be controlled externally.
            Defaults to current UTC time if not provided.
        correlation_id: Correlation ID for request tracing across services.
            Propagated from upstream to enable end-to-end request tracing.
        envelope_id: Source envelope ID for causality tracking. Links this
            effect execution to the originating event envelope.
        dispatch_id: Dispatch operation ID for request tracing. Uniquely identifies
            a single dispatch() call. All handlers in the same dispatch share this ID.
            None for legacy/custom execution paths outside the dispatch engine.
        trace_id: Optional distributed tracing ID (UUID, e.g., OpenTelemetry trace).
            Used for integration with observability platforms.
        span_id: Optional span ID (UUID) within the trace. Identifies this effect
            execution as a span in the distributed trace.
        retry_attempt: Current retry attempt number (0 = first attempt).
            Used for exponential backoff calculations and retry limit checks.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import UTC, datetime
        >>>
        >>> # Deterministic testing with injected time
        >>> test_time = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
        >>> context = ModelEffectContext(
        ...     correlation_id=uuid4(),
        ...     envelope_id=uuid4(),
        ...     now=test_time,
        ...     retry_attempt=2,  # Third attempt
        ... )
        >>> # Calculate backoff based on retry_attempt
        >>> backoff_ms = 1000 * (2 ** context.retry_attempt)  # 4000ms
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Time injection - effects CAN access this
    now: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Injected current time for retry/metrics calculations. Enables deterministic testing.",
    )

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

    # Effect-specific context
    retry_attempt: int = Field(
        default=0,
        ge=0,
        description="Current retry attempt number (0 = first attempt).",
    )

"""
Orchestrator handler context with time injection support.

This module provides the ModelOrchestratorContext class that supplies
runtime context for orchestrator handler invocations, including time
injection for deterministic deadline and timeout calculations.

Thread Safety:
    ModelOrchestratorContext is immutable (frozen=True) and thread-safe.
    All instances are read-only after creation, making them safe to share
    across threads without synchronization.

Key Features:
    - Time injection via `now` field for deterministic testing
    - Correlation ID for request tracing across services
    - Envelope ID for causality tracking
    - Optional distributed tracing support (trace_id, span_id)

Example:
    >>> from uuid import uuid4
    >>> from datetime import UTC, datetime
    >>> from omnibase_core.models.orchestrator import ModelOrchestratorContext
    >>>
    >>> # Create context with current time (production)
    >>> context = ModelOrchestratorContext(
    ...     correlation_id=uuid4(),
    ...     envelope_id=uuid4(),
    ... )
    >>>
    >>> # Create context with fixed time (testing)
    >>> fixed_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
    >>> test_context = ModelOrchestratorContext(
    ...     now=fixed_time,
    ...     correlation_id=uuid4(),
    ...     envelope_id=uuid4(),
    ... )

See Also:
    - omnibase_core.nodes.node_orchestrator: NodeOrchestrator implementation
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md: Tutorial
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelOrchestratorContext"]


class ModelOrchestratorContext(BaseModel):
    """
    Context for orchestrator handler invocations.

    Provides time injection for deadline and timeout calculations.
    Orchestrators may use `now` for workflow timing decisions such as
    calculating deadlines, checking timeouts, and scheduling future steps.

    The `now` field enables deterministic testing by allowing injection
    of a fixed timestamp instead of relying on wall-clock time.

    Attributes:
        now: Injected current time for deadline/timeout calculations.
            Defaults to UTC-aware current time. Enables deterministic testing
            by allowing injection of fixed timestamps.
        correlation_id: Correlation ID for request tracing across services.
            Used to correlate related events and operations.
        envelope_id: Source envelope ID for causality tracking.
            Links this context to the originating event envelope.
        dispatch_id: Dispatch operation ID for request tracing. Uniquely identifies
            a single dispatch() call. All handlers in the same dispatch share this ID.
            None for legacy/custom execution paths outside the dispatch engine.
        trace_id: Optional distributed tracing ID (UUID) for integration with
            observability platforms (e.g., OpenTelemetry, Jaeger).
        span_id: Optional span ID (UUID) within the trace for fine-grained
            operation tracking.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> # Calculate deadline based on injected time
        >>> from datetime import timedelta
        >>> from omnibase_core.constants import TIMEOUT_DEFAULT_MS
        >>> timeout_ms = TIMEOUT_DEFAULT_MS  # 30 seconds
        >>> deadline = context.now + timedelta(milliseconds=timeout_ms)
        >>> # Use context.now for consistent time injection (not datetime.now)
        >>> if context.now > deadline:
        ...     raise TimeoutError("Operation exceeded deadline")
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # Time injection - orchestrators CAN access this for deadline calculations
    now: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description=(
            "Injected current time for deadline/timeout calculations. "
            "Enables deterministic testing."
        ),
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

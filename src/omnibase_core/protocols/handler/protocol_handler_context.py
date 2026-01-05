"""Protocol for handler execution context.

This module defines ProtocolHandlerContext, the interface for execution context
passed to message handlers during dispatch. All node-specific context models
(ModelComputeContext, ModelEffectContext, ModelReducerContext, ModelOrchestratorContext)
implement this protocol.

Thread Safety:
    All context implementations are frozen (immutable) after creation, making them
    thread-safe for concurrent read access.

Design Rationale:
    The protocol defines the common causality tracking fields that all handlers need:
    - correlation_id: Request tracing across services
    - envelope_id: Links handler invocation to triggering event
    - trace_id/span_id: Optional OpenTelemetry integration

    Node-specific fields (e.g., `now` for Effect/Orchestrator, `retry_attempt` for Effect)
    are defined on the concrete models, not the protocol.

See Also:
    - omnibase_core.models.compute.model_compute_context: Compute handler context (pure)
    - omnibase_core.models.effect.model_effect_context: Effect handler context (with time)
    - omnibase_core.models.reducer.model_reducer_context: Reducer handler context (pure)
    - omnibase_core.models.orchestrator.model_orchestrator_context: Orchestrator context (with time)
    - omnibase_core.runtime.runtime_message_dispatch: Uses this for handler dispatch
"""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolHandlerContext(Protocol):
    """Protocol for handler execution context.

    All context models (Compute, Effect, Reducer, Orchestrator) implement this
    protocol. Handlers receive a context implementing this protocol during
    message dispatch.

    The protocol defines causality tracking fields common to all handlers.
    Node-specific fields are available on the concrete context types.

    Attributes:
        correlation_id: Correlation ID for request tracing across services.
            Used to track causality chains through the system.
        envelope_id: Source envelope ID for causality tracking. Links this
            handler invocation to its triggering event envelope.
        trace_id: Optional distributed tracing ID (UUID) for observability systems
            (e.g., OpenTelemetry, Jaeger). None if not using distributed tracing.
        span_id: Optional span ID (UUID) within the distributed trace.
            None if not using distributed tracing.
        dispatch_id: Optional dispatch operation ID for request tracing.
            Uniquely identifies a single dispatch() call in the message dispatch
            engine. None for legacy/custom execution paths.

    Example:
        >>> def my_handler(
        ...     envelope: ModelEventEnvelope[MyPayload],
        ...     context: ProtocolHandlerContext,
        ... ) -> ModelHandlerOutput:
        ...     # Access common context fields
        ...     logger.info(f"Processing request {context.correlation_id}")
        ...
        ...     # For node-specific fields, use concrete type
        ...     if isinstance(context, ModelEffectContext):
        ...         backoff_ms = 1000 * (2 ** context.retry_attempt)
    """

    @property
    def correlation_id(self) -> UUID:
        """Correlation ID for request tracing across services."""
        ...

    @property
    def envelope_id(self) -> UUID:
        """Source envelope ID for causality tracking."""
        ...

    @property
    def trace_id(self) -> UUID | None:
        """Optional distributed tracing ID (e.g., OpenTelemetry trace ID)."""
        ...

    @property
    def span_id(self) -> UUID | None:
        """Optional span ID within the trace (e.g., OpenTelemetry span ID)."""
        ...

    @property
    def dispatch_id(self) -> UUID | None:
        """Optional dispatch operation ID for request tracing.

        The dispatch_id uniquely identifies a single dispatch() call in the
        message dispatch engine. All handlers invoked during that dispatch
        share the same dispatch_id, enabling correlation of handler outputs
        back to the originating dispatch operation.

        Returns None for legacy/custom execution paths that don't go through
        the dispatch engine. When executing via MessageDispatchEngine.dispatch(),
        this will always be non-None.
        """
        ...


__all__ = ["ProtocolHandlerContext"]

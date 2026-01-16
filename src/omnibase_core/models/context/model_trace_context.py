"""Trace context model for distributed tracing and correlation.

This module provides ModelTraceContext, a typed context model for tracking
distributed traces, spans, and request correlations across services.

Thread Safety:
    ModelTraceContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelOperationalContext: Operation-level context
    - ModelErrorDetails: Error handling with context support
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ModelTraceContext(BaseModel):
    """Typed context for distributed tracing and correlation tracking.

    This model provides structured fields for tracking requests across
    distributed systems, enabling trace aggregation and debugging.

    Use Cases:
        - Distributed tracing across microservices
        - Request correlation in log aggregation
        - Span tracking for performance analysis
        - Error context propagation

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        trace_id: Unique identifier for the entire trace/request flow.
        span_id: Unique identifier for the current span within the trace.
        correlation_id: Business-level correlation identifier for related operations.

    Example:
        Basic trace context::

            from omnibase_core.models.context import ModelTraceContext
            from uuid import uuid4

            context = ModelTraceContext(
                trace_id=uuid4(),
                span_id=uuid4(),
                correlation_id=uuid4(),
            )

        Minimal context (trace_id is required)::

            context = ModelTraceContext(
                trace_id=uuid4(),
            )

    See Also:
        - ModelOperationalContext: For operation-level metadata
        - ModelErrorDetails: Uses context for error tracking
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    trace_id: uuid.UUID = Field(
        description="Unique identifier for the entire trace/request flow",
    )
    span_id: uuid.UUID | None = Field(
        default=None,
        description="Unique identifier for the current span within the trace",
    )
    correlation_id: uuid.UUID | None = Field(
        default=None,
        description="Business-level correlation identifier for related operations",
    )

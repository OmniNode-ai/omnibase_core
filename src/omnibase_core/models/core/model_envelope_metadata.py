"""
ModelEnvelopeMetadata - Typed metadata for ModelOnexEnvelope.

This model provides strongly typed metadata fields for envelope messages,
replacing the untyped dict[str, Any] pattern. It includes common fields for
distributed tracing, request tracking, and custom headers.

Architecture:
    Provides structured metadata with:
    - Distributed tracing support (trace_id, span_id, parent_span_id)
    - Request tracking (request_id)
    - Protocol headers (headers dict with str values)
    - Custom tags/labels (tags dict with str values)

Usage:
    .. code-block:: python

        from omnibase_core.models.core.model_envelope_metadata import (
            ModelEnvelopeMetadata,
        )

        # Create metadata with tracing info
        metadata = ModelEnvelopeMetadata(
            trace_id="abc123",
            span_id="def456",
            request_id="req-789",
            headers={"content-type": "application/json"},
            tags={"environment": "production"},
        )

        # Access typed fields
        print(f"Trace: {metadata.trace_id}")
        print(f"Request: {metadata.request_id}")

Part of omnibase_core framework - provides typed metadata for event envelopes.

Related:
    - : ModelOnexEnvelope refactoring
    - ModelOnexEnvelope: Uses this model for its metadata field

.. versionadded:: 0.3.6
    Introduced as typed replacement for dict[str, Any] metadata.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEnvelopeMetadata(BaseModel):
    """
    Typed metadata for ModelOnexEnvelope.

    This model provides strongly typed fields for common envelope metadata
    including distributed tracing, request tracking, headers, and tags.

    Attributes:
        trace_id (str | None): Distributed tracing ID (e.g., OpenTelemetry trace ID).
            Used to correlate logs and spans across services in a distributed system.
            Defaults to None.

        request_id (str | None): Request identifier for tracking individual requests.
            Typically set by the originating service or API gateway.
            Defaults to None.

        span_id (str | None): Tracing span ID for the current operation.
            Combined with trace_id, identifies a specific unit of work.
            Defaults to None.

        parent_span_id (str | None): Parent span ID for trace context propagation.
            Links this span to its parent in a distributed trace.
            Defaults to None.

        headers (dict[str, str]): HTTP/protocol headers as string key-value pairs.
            Use for content-type, authorization headers (sanitized), custom headers.
            Defaults to an empty dict (new dict per instance).

        tags (dict[str, str]): Custom tags/labels for categorization and filtering.
            Use for environment, version, feature flags, etc.
            Defaults to an empty dict (new dict per instance).

    Example:
        .. code-block:: python

            from omnibase_core.models.core.model_envelope_metadata import (
                ModelEnvelopeMetadata,
            )

            # Full metadata with all fields
            metadata = ModelEnvelopeMetadata(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                parent_span_id="a2fb4a1d1a96d312",
                request_id="req-abc123",
                headers={
                    "content-type": "application/json",
                    "x-custom-header": "value",
                },
                tags={
                    "environment": "production",
                    "version": "1.2.3",
                },
            )

            # Minimal metadata (all defaults)
            minimal = ModelEnvelopeMetadata()

    Thread Safety:
        This model uses ``frozen=False`` (mutable) with ``validate_assignment=True``
        for consistency with ModelOnexEnvelope.

        **Concurrent Access Guidelines:**

        - **Read Access**: Thread-safe for simultaneous reads.
        - **Write Access**: NOT thread-safe. Use external synchronization
          if multiple threads may modify the same instance.

    See Also:
        - :class:`~omnibase_core.models.core.model_onex_envelope.ModelOnexEnvelope`:
          The envelope that uses this metadata model
        - :class:`~omnibase_core.protocols.event_bus.ProtocolEventContext`:
          Protocol defining trace context properties

    .. versionadded:: 0.3.6
        Initial implementation with typed metadata fields.
    """

    # ==========================================================================
    # Distributed Tracing Fields
    # ==========================================================================

    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing ID (e.g., OpenTelemetry trace ID). "
        "Used to correlate logs and spans across services.",
    )

    span_id: str | None = Field(
        default=None,
        description="Tracing span ID for the current operation. "
        "Combined with trace_id, identifies a specific unit of work.",
    )

    parent_span_id: str | None = Field(
        default=None,
        description="Parent span ID for trace context propagation. "
        "Links this span to its parent in a distributed trace.",
    )

    # ==========================================================================
    # Request Tracking
    # ==========================================================================

    request_id: str | None = Field(
        default=None,
        description="Request identifier for tracking individual requests. "
        "Typically set by the originating service or API gateway.",
    )

    # ==========================================================================
    # Protocol Headers (typed as str values)
    # ==========================================================================

    # Performance Note: default_factory=dict creates a new dict per instance.
    # This is intentional and correct - see ModelOnexEnvelope for details.
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP/protocol headers as string key-value pairs. "
        "Use for content-type, custom headers, etc.",
    )

    # ==========================================================================
    # Custom Tags/Labels (typed as str values)
    # ==========================================================================

    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Custom tags/labels for categorization and filtering. "
        "Use for environment, version, feature flags, etc.",
    )

    # ==========================================================================
    # Model Configuration
    # ==========================================================================

    model_config = ConfigDict(
        frozen=False,  # Allow modification for consistency with envelope
        validate_assignment=True,  # Validate on attribute assignment
    )

    # ==========================================================================
    # String Representation
    # ==========================================================================

    def __str__(self) -> str:
        """
        Human-readable representation of the metadata.

        Returns a concise string showing key tracing fields if present.

        Returns:
            str: Formatted string like:
                "ModelEnvelopeMetadata[trace=abc123, req=req-789]"
        """
        parts = []
        if self.trace_id:
            parts.append(f"trace={self.trace_id[:8]}")
        if self.request_id:
            parts.append(f"req={self.request_id[:12]}")
        if self.span_id:
            parts.append(f"span={self.span_id[:8]}")

        if parts:
            return f"ModelEnvelopeMetadata[{', '.join(parts)}]"
        return "ModelEnvelopeMetadata[empty]"

    # ==========================================================================
    # Convenience Methods
    # ==========================================================================

    def has_trace_context(self) -> bool:
        """
        Check if this metadata has distributed tracing context.

        Returns:
            bool: True if trace_id is set, False otherwise.
        """
        return self.trace_id is not None

    def has_request_context(self) -> bool:
        """
        Check if this metadata has request tracking context.

        Returns:
            bool: True if request_id is set, False otherwise.
        """
        return self.request_id is not None

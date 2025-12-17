"""
TypedDict for event envelope dictionary representation.

Used by ModelEventEnvelope.to_dict_lazy() method.
"""

from typing import TypedDict
from uuid import UUID


class TypedDictEventEnvelopeDict(TypedDict, total=False):
    """
    TypedDict for event envelope lazy dictionary.

    Used for ModelEventEnvelope.to_dict_lazy() return type.

    Note: This represents the serialized form where UUIDs become strings
    and ModelSemVer becomes a string representation. Some fields are optional
    (None values are preserved in the output).

    Attributes:
        envelope_id: Unique envelope identifier (as string)
        envelope_timestamp: Envelope creation timestamp (ISO format)
        correlation_id: Correlation ID for request tracing (as string, or None)
        source_tool: Identifier of source tool (or None)
        target_tool: Identifier of target tool (or None)
        priority: Request priority (1-10)
        timeout_seconds: Optional timeout in seconds (or None)
        retry_count: Number of retry attempts
        request_id: Request identifier (UUID or None)
        trace_id: Distributed trace identifier (UUID or None)
        span_id: Trace span identifier (UUID or None)
        metadata: Envelope metadata dictionary
        security_context: Security context dictionary (or None)
        onex_version: ONEX standard version (as string)
        envelope_version: Envelope schema version (as string)
        payload: The wrapped event payload (lazily evaluated)
    """

    envelope_id: str
    envelope_timestamp: str
    correlation_id: str | None
    source_tool: str | None
    target_tool: str | None
    priority: int
    timeout_seconds: int | None
    retry_count: int
    request_id: UUID | None
    trace_id: UUID | None
    span_id: UUID | None
    metadata: dict[str, object]
    security_context: dict[str, object] | None
    onex_version: str
    envelope_version: str
    payload: object


__all__ = ["TypedDictEventEnvelopeDict"]

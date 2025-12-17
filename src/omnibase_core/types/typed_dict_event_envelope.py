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

    Note: This represents the lazy-evaluated form where envelope_id and
    correlation_id are converted to strings, but request_id, trace_id, and
    span_id remain as UUID objects. ModelSemVer fields become string
    representations. Some fields are optional (None values are preserved).

    Attributes:
        envelope_id: Unique envelope identifier (converted to string)
        envelope_timestamp: Envelope creation timestamp (ISO format string)
        correlation_id: Correlation ID for request tracing (converted to string, or None)
        source_tool: Identifier of source tool (or None)
        target_tool: Identifier of target tool (or None)
        priority: Request priority (1-10)
        timeout_seconds: Optional timeout in seconds (or None)
        retry_count: Number of retry attempts
        request_id: Request identifier (UUID object or None, not converted)
        trace_id: Distributed trace identifier (UUID object or None, not converted)
        span_id: Trace span identifier (UUID object or None, not converted)
        metadata: Envelope metadata dictionary
        security_context: Security context dictionary (or None)
        onex_version: ONEX standard version (converted to string)
        envelope_version: Envelope schema version (converted to string)
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

"""
Protocol for standardized headers for ONEX event bus messages.

This module provides the ProtocolEventBusHeaders protocol definition
for standardized header handling in event-driven messaging.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import (
    LiteralEventPriority,
    ProtocolDateTime,
    ProtocolSemVer,
)


@runtime_checkable
class ProtocolEventBusHeaders(Protocol):
    """
    Protocol for standardized headers for ONEX event bus messages.

    Enforces strict interoperability across all agents and prevents
    integration failures from header naming inconsistencies.
    """

    @property
    def content_type(self) -> str:
        """Get content type (e.g., 'application/json')."""
        ...

    @property
    def correlation_id(self) -> UUID:
        """Get correlation ID for distributed tracing."""
        ...

    @property
    def message_id(self) -> UUID:
        """Get unique message ID."""
        ...

    @property
    def timestamp(self) -> ProtocolDateTime:
        """Get message timestamp."""
        ...

    @property
    def source(self) -> str:
        """Get message source identifier."""
        ...

    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        ...

    @property
    def schema_version(self) -> ProtocolSemVer:
        """Get schema version."""
        ...

    @property
    def destination(self) -> str | None:
        """Get optional destination."""
        ...

    @property
    def trace_id(self) -> str | None:
        """Get OpenTelemetry trace ID."""
        ...

    @property
    def span_id(self) -> str | None:
        """Get OpenTelemetry span ID."""
        ...

    @property
    def parent_span_id(self) -> str | None:
        """Get parent span ID for trace context."""
        ...

    @property
    def operation_name(self) -> str | None:
        """Get operation name."""
        ...

    @property
    def priority(self) -> LiteralEventPriority | None:
        """Get message priority."""
        ...

    @property
    def routing_key(self) -> str | None:
        """Get routing key."""
        ...

    @property
    def partition_key(self) -> str | None:
        """Get partition key."""
        ...

    @property
    def retry_count(self) -> int | None:
        """Get retry count."""
        ...

    @property
    def max_retries(self) -> int | None:
        """Get max retries."""
        ...

    @property
    def ttl_seconds(self) -> int | None:
        """Get time-to-live in seconds."""
        ...


__all__ = ["ProtocolEventBusHeaders"]

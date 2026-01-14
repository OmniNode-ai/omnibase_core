"""
Protocol for standardized headers for ONEX event bus messages.

This module provides the ProtocolEventBusHeaders protocol definition
for standardized header handling in event-driven messaging.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.enums import EnumEventPriority
from omnibase_core.protocols.base import (
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
    def content_type(self) -> str: ...

    @property
    def correlation_id(self) -> UUID: ...

    @property
    def message_id(self) -> UUID: ...

    @property
    def timestamp(self) -> ProtocolDateTime: ...

    @property
    def source(self) -> str: ...

    @property
    def event_type(self) -> str: ...

    @property
    def schema_version(self) -> ProtocolSemVer: ...

    @property
    def destination(self) -> str | None: ...

    @property
    def trace_id(self) -> str | None: ...

    @property
    def span_id(self) -> str | None: ...

    @property
    def parent_span_id(self) -> str | None: ...

    @property
    def operation_name(self) -> str | None: ...

    @property
    def priority(self) -> EnumEventPriority | None: ...

    @property
    def routing_key(self) -> str | None: ...

    @property
    def partition_key(self) -> str | None: ...

    @property
    def retry_count(self) -> int | None: ...

    @property
    def max_retries(self) -> int | None: ...

    @property
    def ttl_seconds(self) -> int | None: ...


__all__ = ["ProtocolEventBusHeaders"]

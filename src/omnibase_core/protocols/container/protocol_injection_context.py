"""
Protocol for dependency injection context.

This module provides the ProtocolInjectionContext protocol which
defines the interface for injection context tracking including
resolution status, error handling, and dependency path tracking.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.enums import EnumInjectionScope, EnumServiceResolutionStatus
from omnibase_core.protocols.base import (
    ContextValue,
    ProtocolDateTime,
)


@runtime_checkable
class ProtocolInjectionContext(Protocol):
    """
    Protocol for dependency injection context.

    Defines the interface for injection context tracking including
    resolution status, error handling, and dependency path tracking.
    """

    context_id: UUID
    target_service_id: UUID
    scope: EnumInjectionScope
    resolved_dependencies: dict[str, ContextValue]
    injection_time: ProtocolDateTime
    resolution_status: EnumServiceResolutionStatus
    error_details: str | None
    resolution_path: list[UUID]
    metadata: dict[str, ContextValue]


__all__ = ["ProtocolInjectionContext"]

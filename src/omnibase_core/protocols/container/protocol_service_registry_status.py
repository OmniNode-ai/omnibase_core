"""
Protocol for service registry status information.

This module provides the ProtocolServiceRegistryStatus protocol which
defines the interface for comprehensive registry status reporting
including registration statistics, health monitoring, and performance metrics.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import (
    LiteralHealthStatus,
    LiteralInjectionScope,
    LiteralOperationStatus,
    LiteralServiceLifecycle,
    ProtocolDateTime,
)


@runtime_checkable
class ProtocolServiceRegistryStatus(Protocol):
    """
    Protocol for service registry status information.

    Defines the interface for comprehensive registry status reporting
    including registration statistics, health monitoring, and performance metrics.
    """

    registry_id: UUID
    status: LiteralOperationStatus
    message: str
    total_registrations: int
    active_instances: int
    failed_registrations: int
    circular_dependencies: int
    lifecycle_distribution: dict[LiteralServiceLifecycle, int]
    scope_distribution: dict[LiteralInjectionScope, int]
    health_summary: dict[LiteralHealthStatus, int]
    memory_usage_bytes: int | None
    average_resolution_time_ms: float | None
    last_updated: ProtocolDateTime


__all__ = ["ProtocolServiceRegistryStatus"]

"""
Protocol for dependency graph information.

This module provides the ProtocolDependencyGraph protocol which
defines the interface for dependency graph analysis including
dependency chains, circular reference detection, and resolution ordering.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolDependencyGraph(Protocol):
    """
    Protocol for dependency graph information.

    Defines the interface for dependency graph analysis including
    dependency chains, circular reference detection, and resolution ordering.
    """

    service_id: UUID
    dependencies: list[UUID]
    dependents: list[UUID]
    depth_level: int
    circular_references: list[UUID]
    resolution_order: list[UUID]
    metadata: dict[str, ContextValue]


__all__ = ["ProtocolDependencyGraph"]

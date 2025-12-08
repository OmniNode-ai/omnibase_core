"""
Protocol for dependency graph information.

This module provides the ProtocolDependencyGraph protocol which
defines the interface for dependency graph analysis including
dependency chains, circular reference detection, and resolution ordering.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolDependencyGraph(Protocol):
    """
    Protocol for dependency graph information.

    Defines the interface for dependency graph analysis including
    dependency chains, circular reference detection, and resolution ordering.
    """

    service_id: str
    dependencies: list[str]
    dependents: list[str]
    depth_level: int
    circular_references: list[str]
    resolution_order: list[str]
    metadata: dict[str, ContextValue]


__all__ = ["ProtocolDependencyGraph"]

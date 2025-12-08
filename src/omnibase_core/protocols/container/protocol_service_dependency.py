"""
Protocol for service dependency information.

This module provides the ProtocolServiceDependency protocol which
defines the interface for service dependency metadata including
version constraints, circular dependency detection, and injection points.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue, ProtocolSemVer


@runtime_checkable
class ProtocolServiceDependency(Protocol):
    """
    Protocol for service dependency information.

    Defines the interface for service dependency metadata including
    version constraints, circular dependency detection, and injection points.
    """

    dependency_name: str
    dependency_interface: str
    dependency_version: ProtocolSemVer | None
    is_required: bool
    is_circular: bool
    injection_point: str
    default_value: Any | None
    metadata: dict[str, ContextValue]

    async def validate_dependency(self) -> bool:
        """Validate that dependency constraints are satisfied."""
        ...

    def is_satisfied(self) -> bool:
        """Check if dependency requirements are currently met."""
        ...


__all__ = ["ProtocolServiceDependency"]

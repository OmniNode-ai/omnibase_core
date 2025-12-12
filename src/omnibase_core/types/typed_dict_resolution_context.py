"""TypedDict for service resolution context."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class TypedDictResolutionContext(TypedDict, total=False):
    """
    TypedDict for service resolution context.

    Provides typed context information during service resolution,
    including scope information, correlation tracking, and resolver hints.

    Attributes:
        scope_id: Optional scope identifier for scoped resolution
        correlation_id: Optional correlation ID for request tracking
        parent_resolution_id: ID of parent resolution in chain
        timeout_ms: Resolution timeout in milliseconds
        prefer_cached: Whether to prefer cached instances
        require_healthy: Whether to require healthy service instances
        resolver_hints: Additional hints for the resolver (string keys)
    """

    scope_id: UUID
    correlation_id: UUID
    parent_resolution_id: UUID
    timeout_ms: int
    prefer_cached: bool
    require_healthy: bool
    resolver_hints: dict[str, str]


__all__ = ["TypedDictResolutionContext"]

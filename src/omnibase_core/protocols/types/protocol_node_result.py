"""
ProtocolNodeResult - Protocol for node results.

This module provides the protocol definition for node workflow results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue

if TYPE_CHECKING:
    from omnibase_core.protocols.types.protocol_state import ProtocolState


@runtime_checkable
class ProtocolNodeResult(Protocol):
    """
    Protocol for node workflow results.

    Defines the interface for result objects from dispatch_async operations.
    """

    value: ProtocolState | ContextValue | None
    is_success: bool
    is_failure: bool
    error: object | None
    trust_score: float
    provenance: list[str]
    metadata: dict[str, ContextValue]
    events: list[object]
    state_delta: dict[str, ContextValue]

    async def validate_result(self) -> bool:
        """Validate result structure."""
        ...

    def is_successful(self) -> bool:
        """Check if result represents success."""
        ...


__all__ = ["ProtocolNodeResult"]

"""
Protocol defining the minimal interface for event envelopes.

This module provides the ProtocolEventEnvelope generic protocol definition
for event envelope handling without circular dependencies.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

# Define covariant type variable for generic protocol
T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class ProtocolEventEnvelope(Protocol[T_co]):
    """
    Protocol defining the minimal interface for event envelopes.

    This protocol allows mixins to type-hint envelope parameters without
    importing the concrete ModelEventEnvelope class, breaking circular dependencies.
    """

    async def get_payload(self) -> T_co:
        """Get the wrapped event payload."""
        ...


__all__ = ["ProtocolEventEnvelope"]

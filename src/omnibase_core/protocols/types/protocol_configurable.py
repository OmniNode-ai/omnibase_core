"""
ProtocolConfigurable - Protocol for configurable objects.

This module provides the protocol definition for objects that can be configured.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolConfigurable(Protocol):
    """
    Protocol for objects that can be configured.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_configurable_marker__: Literal[True]

    def configure(self, **kwargs: ContextValue) -> None:
        """Apply configuration to the object."""
        ...


__all__ = ["ProtocolConfigurable"]

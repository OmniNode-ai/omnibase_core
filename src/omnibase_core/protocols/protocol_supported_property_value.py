"""
Supported property value protocol for typed properties.

This module defines the protocol for values that can be stored as environment
properties in the typed property system.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSupportedPropertyValue(Protocol):
    """Protocol for values that can be stored as environment properties."""

    def __str__(self) -> str:
        """
        Must be convertible to string for serialization.

        Returns:
            String representation of the value
        """
        ...

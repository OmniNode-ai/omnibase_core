"""
Protocol for types that can be stored in metadata.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSupportedMetadataType(Protocol):
    """Protocol for types that can be stored in metadata."""

    def __str__(self) -> str:
        """Must be convertible to string."""
        ...

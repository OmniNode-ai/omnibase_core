"""
Filter Value Protocol.

Protocol for values that can be used in filters.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolFilterValue(Protocol):
    """Protocol for values that can be used in filters."""

    pass


# Export for use
__all__ = ["ProtocolFilterValue"]

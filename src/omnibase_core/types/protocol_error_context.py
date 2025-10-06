"""ProtocolErrorContext.

Protocol for error context types.

Both BasicErrorContext and ModelErrorContext should implement this
protocol to allow interchangeable use.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolErrorContext(Protocol):
    """
    Protocol for error context types.

    Both BasicErrorContext and ModelErrorContext should implement this
    protocol to allow interchangeable use.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict[str, Any]ionary representation."""
        ...

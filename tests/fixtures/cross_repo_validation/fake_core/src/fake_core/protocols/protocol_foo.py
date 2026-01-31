"""Public protocol - allowed for cross-repo import."""

from __future__ import annotations

from typing import Protocol


class ProtocolFoo(Protocol):
    """Sample protocol for cross-repo use."""

    def do_something(self) -> str:
        """Do something and return result."""
        ...

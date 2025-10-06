from __future__ import annotations

"""
ModelProtocolValidatable

Protocol for values that can validate themselves.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelProtocolValidatable(Protocol):
    """Protocol for values that can validate themselves."""

    def is_valid(self) -> bool:
        """Check if the value is valid."""
        ...

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        ...

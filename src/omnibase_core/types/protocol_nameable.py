"""
Nameable Protocol

Protocol for objects that can be named and renamed.

This protocol defines the interface for objects that support naming,
providing a consistent pattern for name management across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Protocol


class Nameable(Protocol):
    """
    Protocol for objects that can be named and renamed.

    This protocol provides a consistent interface for name management,
    requiring objects to implement both get_name and set_name methods.

    Key Features:
    - Bidirectional name management
    - String-based naming
    - Consistent naming interface
    - Designed for ONEX architecture compliance
    """

    def get_name(self) -> str:
        """
        Get the name of this object.

        Returns:
            str: Current name of the object
        """
        ...

    def set_name(self, name: str) -> None:
        """
        Set the name of this object.

        Args:
            name: New name for the object
        """
        ...

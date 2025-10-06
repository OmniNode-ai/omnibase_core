"""
Identifiable Protocol

Protocol for objects that have a unique identifier.

This protocol defines the interface for objects that can be identified
through a unique ID property, providing a consistent pattern for
identification across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Protocol


class Identifiable(Protocol):
    """
    Protocol for objects that have a unique identifier.

    This protocol provides a consistent interface for identification,
    requiring objects to have an id property that returns a string.

    Key Features:
    - String-based identification
    - Simple property interface
    - Consistent identification pattern
    - Designed for ONEX architecture compliance
    """

    @property
    def id(self) -> str:
        """
        Get the unique identifier for this object.

        Returns:
            str: Unique identifier string
        """
        ...

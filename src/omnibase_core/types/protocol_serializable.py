from typing import Dict

"""
Serializable Protocol

Protocol for objects that can be serialized to dictionary format.

This protocol defines the interface for objects that can be serialized,
providing a consistent pattern for serialization across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Any, Protocol


class Serializable(Protocol):
    """
    Protocol for objects that can be serialized to dictionary format.

    This protocol provides a consistent interface for serialization,
    requiring objects to implement a serialize method that returns
    a dictionary representation.

    Key Features:
    - Dictionary-based serialization
    - Simple method interface
    - Consistent serialization pattern
    - Designed for ONEX architecture compliance
    """

    def serialize(self) -> dict[str, Any]:
        """
        Serialize this object to dictionary format.

        Returns:
            dict[str, Any]: Dictionary representation of the object
        """
        ...

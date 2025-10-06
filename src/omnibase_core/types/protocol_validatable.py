"""
ProtocolValidatable Protocol

Protocol for objects that can validate their own state.

This protocol defines the interface for objects that can perform
self-validation, providing a consistent pattern for validation
across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Protocol


class ProtocolValidatable(Protocol):
    """
    Protocol for objects that can validate their own state.

    This protocol provides a consistent interface for validation,
    requiring objects to implement a validate_instance method that
    returns a boolean indicating validity.

    Key Features:
    - Boolean validation result
    - Simple method interface
    - Consistent validation pattern
    - Designed for ONEX architecture compliance
    """

    def validate_instance(self) -> bool:
        """
        Validate the current state of this object.

        Returns:
            bool: True if the object is in a valid state, False otherwise
        """
        ...

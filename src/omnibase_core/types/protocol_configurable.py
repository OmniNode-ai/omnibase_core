"""
Configurable Protocol

Protocol for objects that can be configured with arbitrary keyword arguments.

This protocol defines the interface for objects that accept configuration
through a configure method, providing a consistent pattern for
configuration management across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Any, Protocol


class Configurable(Protocol):
    """
    Protocol for objects that can be configured with arbitrary keyword arguments.

    This protocol provides a consistent interface for configuration management,
    allowing objects to accept configuration data through a configure method
    that returns a boolean indicating success.

    Key Features:
    - Flexible configuration with arbitrary keyword arguments
    - Boolean return value indicating configuration success
    - Simple interface for broad applicability
    - Designed for ONEX architecture compliance
    """

    def configure(self, **kwargs: Any) -> bool:
        """
        Configure this object with the provided keyword arguments.

        Args:
            **kwargs: Arbitrary configuration keyword arguments

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        ...

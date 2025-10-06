"""
Executable Protocol

Protocol for objects that can be executed with arbitrary arguments.

This protocol defines the interface for objects that can be executed,
providing a consistent pattern for execution across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Any, Protocol


class Executable(Protocol):
    """
    Protocol for objects that can be executed with arbitrary arguments.

    This protocol provides a consistent interface for execution,
    allowing objects to accept positional and keyword arguments through
    an execute method that returns any result.

    Key Features:
    - Flexible execution with arbitrary arguments
    - Any return type for broad applicability
    - Simple interface for executable objects
    - Designed for ONEX architecture compliance
    """

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute this object with the provided arguments.

        Args:
            *args: Arbitrary positional arguments
            **kwargs: Arbitrary keyword arguments

        Returns:
            Any: Result of the execution
        """
        ...

"""
Protocol definition for generic handlers.

This protocol replaces Any type usage when referring to handler objects
by providing a proper protocol interface.
"""

from typing import Protocol


class ProtocolHandler(Protocol):
    """
    Base protocol for all handlers in the ONEX system.

    This protocol defines the minimal interface that all handlers must implement.
    """

    def handle(self, *args, **kwargs) -> bool:
        """
        Handle the given input.

        Args:
            *args: Positional arguments for the handler
            **kwargs: Keyword arguments for the handler

        Returns:
            bool: True if handling was successful, False otherwise
        """
        ...

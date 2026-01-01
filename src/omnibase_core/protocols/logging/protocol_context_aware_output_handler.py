"""
ProtocolContextAwareOutputHandler - Protocol for context-aware log output.

This module provides the protocol definition for output handlers that
route formatted log entries to appropriate destinations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolContextAwareOutputHandler(Protocol):
    """
    Protocol for context-aware log output handlers.

    Routes formatted log entries to appropriate output destinations
    based on log level and context.
    """

    def output_log_entry(
        self,
        formatted_log: str,
        level_name: str,
    ) -> None:
        """
        Output a formatted log entry.

        Args:
            formatted_log: The formatted log string to output
            level_name: The log level name (e.g., "INFO", "ERROR")
        """
        ...


__all__ = ["ProtocolContextAwareOutputHandler"]

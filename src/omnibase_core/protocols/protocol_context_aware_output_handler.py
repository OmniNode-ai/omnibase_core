"""
Protocol for context-aware output handling.

This module provides the ProtocolContextAwareOutputHandler protocol which
defines the interface for output handlers used in the ONEX logging infrastructure.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- NO Any types - use structured types for output data
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolContextAwareOutputHandler(Protocol):
    """
    Protocol for context-aware output handling.

    Defines the interface for output handlers that route formatted log
    entries to appropriate destinations based on context. Used by the
    ONEX logging infrastructure for flexible log output routing.

    The output handler is responsible for:
    - Receiving formatted log entries
    - Routing to appropriate output destinations (console, file, event bus)
    - Handling output based on log level
    - Managing output context and buffering

    Example:
        class MyOutputHandler:
            def output_log_entry(
                self,
                formatted_log: str,
                level_name: str,
            ) -> None:
                if level_name in ("ERROR", "CRITICAL"):
                    print(formatted_log, file=sys.stderr)
                else:
                    print(formatted_log)
    """

    def output_log_entry(
        self,
        formatted_log: str,
        level_name: str,
    ) -> None:
        """
        Output a formatted log entry.

        Args:
            formatted_log: Pre-formatted log string ready for output
            level_name: Name of the log level (e.g., "DEBUG", "INFO", "ERROR")
        """
        ...


__all__ = ["ProtocolContextAwareOutputHandler"]

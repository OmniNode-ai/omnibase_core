"""
Protocol for base tool with logger functionality.

Defines the interface for tools that need standardized logger resolution.
"""

from typing import Protocol

from omnibase_core.nodes.node_logger.protocols.protocol_logger_emit_log_event import \
    ProtocolLoggerEmitLogEvent
from omnibase_core.protocol.protocol_node_registry import ProtocolNodeRegistry


class ProtocolBaseToolWithLogger(Protocol):
    """
    Protocol interface for tools with logger functionality.

    Provides standardized logger resolution interface.
    """

    registry: ProtocolNodeRegistry
    node_id: str
    logger_tool: ProtocolLoggerEmitLogEvent

    def _resolve_logger_tool(self) -> ProtocolLoggerEmitLogEvent:
        """
        Resolve logger tool from registry with proper error handling.

        Returns:
            ProtocolLoggerEmitLogEvent: Configured logger tool instance
        """
        ...

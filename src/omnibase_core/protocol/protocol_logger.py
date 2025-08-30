# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.202429'
# description: Stamped by ToolPython
# entrypoint: python://protocol_logger
# hash: acdddae45e452c0a6de44fa250471b51ec1c8edbff4041180129a32392324405
# last_modified_at: '2025-05-29T14:14:00.269378+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_logger.py
# namespace: python://omnibase.protocol.protocol_logger
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: de679165-4fb9-422e-8b85-35b30fab7495
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Optional, Protocol
from uuid import UUID

from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.model.core.model_log_entry import (LogModelContext,
                                                      ModelLogEntry)


class ProtocolLogger(Protocol):
    """
    Protocol for ONEX logging services that can be resolved from the registry.

    This protocol defines the interface that all logging implementations must
    implement to be compatible with the ONEX logging system.

    Example:
        class MyLogger:
            def emit(self, level: LogLevelEnum, message: str, correlation_id: UUID) -> None:
                ...

            def log(self, entry: ModelLogEntry) -> None:
                ...
    """

    def emit(
        self,
        level: LogLevelEnum,
        message: str,
        correlation_id: UUID,
        context: Optional[LogModelContext] = None,
    ) -> None:
        """
        Emit a log event with the specified level and message.

        Args:
            level: Log level for the message
            message: Log message to emit
            correlation_id: Correlation ID for request tracking
            context: Optional log context for additional metadata
        """
        ...

    def log(self, entry: ModelLogEntry) -> None:
        """
        Log a structured log entry (legacy interface).

        Args:
            entry: Structured log entry to emit
        """
        ...

    def is_level_enabled(self, level: LogLevelEnum) -> bool:
        """
        Check if the specified log level is enabled.

        Args:
            level: Log level to check

        Returns:
            True if the level should be logged, False otherwise
        """
        ...

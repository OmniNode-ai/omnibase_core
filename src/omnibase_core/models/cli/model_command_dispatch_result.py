# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Command dispatch result model for the registry-driven CLI.

Captures the outcome of a single command dispatch operation, including
success status, correlation ID, topic, and error detail.

.. versionadded:: 0.19.0  (OMN-2553)
"""

from __future__ import annotations

__all__ = [
    "ModelCommandDispatchResult",
]

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType


@dataclass(frozen=True)
class ModelCommandDispatchResult:
    """Result of a single command dispatch operation.

    Attributes:
        success: True if dispatch completed without error.
        correlation_id: UUID assigned to this invocation (always present).
        command_ref: The dispatched command's globally namespaced identifier
            (e.g. ``com.omninode.memory.query``).
        invocation_type: The dispatch mechanism that was used.
        topic: Kafka topic published to (for KAFKA_EVENT dispatches).
        error_message: Error detail if ``success`` is False.
        dispatched_at: UTC timestamp of dispatch attempt.

    .. versionadded:: 0.19.0  (OMN-2553)
    """

    success: bool
    correlation_id: str
    command_ref: str
    invocation_type: EnumCliInvocationType
    topic: str | None = field(default=None)
    error_message: str | None = field(default=None)
    dispatched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_json(self) -> str:
        """Serialize this result to a JSON string.

        Returns:
            JSON representation of the dispatch result.
        """
        return json.dumps(
            {
                "success": self.success,
                "correlation_id": self.correlation_id,
                "command_ref": self.command_ref,
                "invocation_type": self.invocation_type.value,
                "topic": self.topic,
                "error_message": self.error_message,
                "dispatched_at": self.dispatched_at.isoformat(),
            },
            sort_keys=True,
        )

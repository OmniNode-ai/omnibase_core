# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol for alert topic publisher (OMN-2563)."""

from __future__ import annotations

from typing import Any, Protocol


class ProtocolAlertTopicPublisher(Protocol):
    """Protocol for publishing anti-gaming alerts to Kafka."""

    async def publish(
        self,
        *,
        topic: str,
        alert_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an alert event to the specified Kafka topic.

        Args:
            topic:      Kafka topic (e.g., '{env}.onex.evt.omnimemory.anti-gaming-alert.v1')
            alert_type: Alert type string (from EnumAlertType.value)
            payload:    JSON-serializable alert payload.
        """
        ...


__all__ = ["ProtocolAlertTopicPublisher"]

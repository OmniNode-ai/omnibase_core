# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""NodeAntiGamingAlerterEffect — publishes anti-gaming alerts to Kafka.

Companion EFFECT node to NodeAntiGamingGuardrailsCompute.
Receives the guardrail output and publishes all alerts to:
    {env}.onex.evt.omnimemory.anti-gaming-alert.v1

Ticket: OMN-2563
"""

from __future__ import annotations

import json
import logging
from typing import ClassVar

from omniintelligence.nodes.node_anti_gaming_alerter_effect.handlers.protocols import (
    ProtocolAlertTopicPublisher,
)
from omniintelligence.nodes.node_anti_gaming_alerter_effect.models.model_alerter_input import (
    ModelAlerterInput,
)
from omniintelligence.nodes.node_anti_gaming_alerter_effect.models.model_alerter_output import (
    ModelAlerterOutput,
)
from omniintelligence.nodes.node_anti_gaming_guardrails_compute.models.model_alert_event import (
    ModelAntiGamingAlertUnion,
    ModelDiversityConstraintViolation,
)

logger = logging.getLogger(__name__)


class NodeAntiGamingAlerterEffect:
    """EFFECT node for publishing anti-gaming alerts to Kafka.

    Receives ModelGuardrailOutput from NodeAntiGamingGuardrailsCompute
    and publishes each alert to the configured Kafka topic.

    Dependencies are injected via constructor:
        - publisher: ProtocolAlertTopicPublisher
    """

    is_stub: ClassVar[bool] = True

    def __init__(
        self,
        *args: object,
        publisher: ProtocolAlertTopicPublisher,
        **kwargs: object,
    ) -> None:
        self._publisher = publisher

    async def execute(self, input_data: ModelAlerterInput) -> ModelAlerterOutput:
        """Publish all alerts from guardrail output to Kafka.

        Args:
            input_data: Alerter input with guardrail output and topic.

        Returns:
            Output with published alert counts.
        """
        output = input_data.guardrail_output
        topic = input_data.kafka_topic
        published_count = 0
        diversity_published = False

        # Publish non-blocking alerts
        for alert in output.alerts:
            payload = self._serialize_alert(alert)
            alert_type_str = str(payload.get("alert_type", "unknown"))
            await self._publisher.publish(
                topic=topic,
                alert_type=alert_type_str,
                payload=payload,
            )
            published_count += 1
            logger.info(
                "Published anti-gaming alert: type=%s run=%s",
                alert_type_str,
                output.run_id,
            )

        # Publish diversity constraint violation (veto)
        if output.diversity_violation is not None:
            payload = self._serialize_alert(output.diversity_violation)
            alert_type_str = str(payload.get("alert_type", "unknown"))
            await self._publisher.publish(
                topic=topic,
                alert_type=alert_type_str,
                payload=payload,
            )
            published_count += 1
            diversity_published = True
            logger.warning(
                "Published diversity constraint violation (VETO): run=%s",
                output.run_id,
            )

        return ModelAlerterOutput(
            run_id=output.run_id,
            alerts_published=published_count,
            diversity_violation_published=diversity_published,
            topic=topic,
        )

    def _serialize_alert(
        self, alert: ModelAntiGamingAlertUnion | ModelDiversityConstraintViolation
    ) -> dict[str, object]:
        """Serialize an alert to a JSON-compatible dict."""
        raw: dict[str, object] = json.loads(alert.model_dump_json())
        return raw


__all__ = ["NodeAntiGamingAlerterEffect"]

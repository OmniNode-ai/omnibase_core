# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Rule-7a definition-B fold: no I/O and no clock."""

from omnimarket.models.delegation.model_routing_feedback import (
    ModelRoutingFeedbackUpdatedEvent,
)
from omnimarket.nodes.node_projection_routing_feedback.models import (
    ModelRoutingFeedbackProjectionResult,
    ModelRoutingFeedbackRow,
)


class HandlerProjectionRoutingFeedback:
    """Carry the producer's cumulative feedback unchanged into one row."""

    def handle(
        self, request: ModelRoutingFeedbackUpdatedEvent
    ) -> ModelRoutingFeedbackProjectionResult:
        row = ModelRoutingFeedbackRow(**request.feedback.model_dump())
        return ModelRoutingFeedbackProjectionResult(rows=(row,))

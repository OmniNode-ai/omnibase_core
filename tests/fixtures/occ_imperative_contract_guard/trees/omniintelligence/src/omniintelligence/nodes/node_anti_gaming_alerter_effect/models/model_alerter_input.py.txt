# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for AntiGamingAlerterEffect node (OMN-2563)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omniintelligence.nodes.node_anti_gaming_guardrails_compute.models.model_guardrail_output import (
    ModelGuardrailOutput,
)


class ModelAlerterInput(BaseModel):
    """Input to the AntiGamingAlerterEffect node."""

    model_config = ConfigDict(frozen=True)

    guardrail_output: ModelGuardrailOutput = Field(
        description="Output from AntiGamingGuardrailsCompute containing alerts."
    )
    kafka_topic: str = Field(
        description="Kafka topic to publish alerts to. "
        "Format: {env}.onex.evt.omnimemory.anti-gaming-alert.v1"
    )


__all__ = ["ModelAlerterInput"]

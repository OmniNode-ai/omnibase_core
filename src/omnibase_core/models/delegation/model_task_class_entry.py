# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTaskClassEntry: declaration for a single task class in the task-class contract (OMN-10614)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_cloud_routing_policy import EnumCloudRoutingPolicy
from omnibase_core.models.delegation.model_definition_of_done import (
    ModelDefinitionOfDone,
)
from omnibase_core.models.delegation.model_escalation_policy import (
    ModelEscalationPolicy,
)


class ModelTaskClassEntry(BaseModel):
    """Declaration for a single task class."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    required_capabilities: list[str] = Field(default_factory=list)
    pricing_ceiling_per_1k_tokens: float = Field(..., ge=0.0)
    latency_sla_p99_ms: int = Field(..., gt=0)
    cloud_routing_policy: EnumCloudRoutingPolicy
    definition_of_done: ModelDefinitionOfDone
    escalation_policy: ModelEscalationPolicy


__all__ = ["ModelTaskClassEntry"]

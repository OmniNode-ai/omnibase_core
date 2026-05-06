# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEscalationPolicy: routing tier escalation policy for task-class contracts (OMN-10614)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelEscalationPolicy(BaseModel):
    """Escalation policy for a task class.

    tier_order defines the sequence of routing tiers tried on escalation.
    max_escalations caps how many times the result can be escalated before
    the delegation is treated as failed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    max_escalations: int = Field(..., ge=0)
    tier_order: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_escalation_bounds(self) -> ModelEscalationPolicy:
        if len(self.tier_order) < self.max_escalations:
            msg = (
                f"tier_order has {len(self.tier_order)} entries but max_escalations is "
                f"{self.max_escalations}; tier_order must have at least max_escalations entries"
            )
            raise ValueError(msg)
        return self


__all__ = ["ModelEscalationPolicy"]

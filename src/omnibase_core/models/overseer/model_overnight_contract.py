# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelOvernightContract — machine-readable contract for overnight pipeline sessions (OMN-10251)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.overseer.model_overnight_halt_condition import (
    ModelOvernightHaltCondition,
)
from omnibase_core.models.overseer.model_overnight_phase_spec import (
    ModelOvernightPhaseSpec,
)
from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "session_id is an overseer correlation string for overnight sessions, "
        "not a system UUID."
    )
)
class ModelOvernightContract(BaseModel):
    """Machine-readable contract for an overnight pipeline session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-version-ok: wire type serialized to YAML at overnight contract boundary
    schema_version: str = "1.0.0"
    session_id: str  # string-id-ok: overseer correlation string for overnight session
    created_at: datetime
    max_cost_usd: float = 5.0
    max_duration_seconds: int = 28800
    dry_run: bool = False
    phases: tuple[ModelOvernightPhaseSpec, ...] = Field(..., min_length=1)
    halt_conditions: tuple[ModelOvernightHaltCondition, ...] = Field(
        default_factory=tuple
    )

    @model_validator(mode="after")
    def _apply_default_halt_conditions(self) -> ModelOvernightContract:
        if self.halt_conditions:
            return self
        object.__setattr__(
            self,
            "halt_conditions",
            (
                ModelOvernightHaltCondition(
                    condition_id="cost_ceiling",
                    description="Stop if accumulated cost exceeds ceiling",
                    check_type="cost_ceiling",
                    threshold=self.max_cost_usd,
                ),
                ModelOvernightHaltCondition(
                    condition_id="phase_failure_limit",
                    description="Stop after 3 consecutive phase failures",
                    check_type="phase_failure_count",
                    threshold=3.0,
                ),
            ),
        )
        return self

    standing_orders: tuple[str, ...] = Field(default_factory=tuple)
    required_outcomes: tuple[str, ...] = Field(
        default_factory=lambda: (
            "merge_sweep_completed",
            "platform_readiness_gate_passed",
        )
    )


__all__ = ["ModelOvernightContract"]

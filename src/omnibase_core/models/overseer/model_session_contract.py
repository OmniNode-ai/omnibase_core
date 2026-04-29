# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSessionContract — machine-readable contract for pipeline sessions (OMN-10251)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.overseer.model_session_halt_condition import (
    ModelSessionHaltCondition,
)
from omnibase_core.models.overseer.model_session_phase_spec import ModelSessionPhaseSpec
from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "session_id is an overseer correlation string for pipeline sessions, "
        "not a system UUID."
    )
)
class ModelSessionContract(BaseModel):
    """Machine-readable contract for a pipeline session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-version-ok: wire type serialized to YAML at session contract boundary
    schema_version: str = "1.0.0"
    session_id: str  # string-id-ok: overseer correlation string for pipeline session
    created_at: datetime
    max_cost_usd: float = 5.0
    max_duration_seconds: int = 28800
    dry_run: bool = False
    phases: tuple[ModelSessionPhaseSpec, ...] = Field(..., min_length=1)
    halt_conditions: tuple[ModelSessionHaltCondition, ...] = Field(
        default_factory=lambda: (
            ModelSessionHaltCondition(
                condition_id="cost_ceiling",
                description="Stop if accumulated cost exceeds ceiling",
                check_type="cost_ceiling",
                threshold=5.0,
            ),
            ModelSessionHaltCondition(
                condition_id="phase_failure_limit",
                description="Stop after 3 consecutive phase failures",
                check_type="phase_failure_count",
                threshold=3.0,
            ),
        )
    )
    standing_orders: tuple[str, ...] = Field(default_factory=tuple)
    required_outcomes: tuple[str, ...] = Field(
        default_factory=lambda: (
            "merge_sweep_completed",
            "platform_readiness_gate_passed",
        )
    )


__all__ = ["ModelSessionContract"]

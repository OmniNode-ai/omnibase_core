# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Autopilot cycle record model for tracking close-out cycle state."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_autopilot_cycle_status import (
    EnumAutopilotCycleStatus,
)
from omnibase_core.enums.governance.enum_autopilot_mode import EnumAutopilotMode
from omnibase_core.models.governance.model_autopilot_step_result import (
    ModelAutopilotStepResult,
)


class ModelAutopilotCycleRecord(BaseModel):
    """Record of a single autopilot close-out cycle.

    Written to: ``$ONEX_STATE_DIR/state/autopilot/{cycle_id}.yaml``
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-version-ok: wire type serialized to YAML at autopilot cycle boundary
    schema_version: str = Field(..., description="Schema version (SemVer)")
    # string-id-ok: opaque autopilot cycle correlation identifier, not a DB primary key
    cycle_id: str = Field(..., description="Unique cycle identifier")
    mode: EnumAutopilotMode = Field(..., description="Autopilot operating mode")
    started_at: datetime = Field(..., description="When cycle started")
    completed_at: datetime | None = Field(
        default=None, description="When cycle completed"
    )
    steps: list[ModelAutopilotStepResult] = Field(
        default_factory=list, description="Per-step results"
    )
    overall_status: EnumAutopilotCycleStatus = Field(
        default=EnumAutopilotCycleStatus.INCOMPLETE,
        description="Cycle completion status",
    )
    consecutive_noop_count: int = Field(
        default=0,
        description="Prior consecutive cycles with zero tickets",
        ge=0,
    )

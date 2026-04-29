# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Autopilot step result model for a single pipeline step."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.governance.enum_autopilot_step_status import (
    EnumAutopilotStepStatus,
)


class ModelAutopilotStepResult(BaseModel):
    """Result for a single autopilot pipeline step.

    Skipped steps must provide a non-empty reason.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    step: str = Field(
        ..., description="Step name (e.g., merge-sweep, integration-sweep)"
    )
    status: EnumAutopilotStepStatus = Field(..., description="Step completion status")
    reason: str | None = Field(
        default=None, description="Why step was skipped or failed"
    )
    duration_seconds: float = Field(
        default=0.0, description="Wall-clock execution time"
    )

    @field_validator("reason")
    @classmethod
    def skipped_requires_reason(cls, v: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("status") == EnumAutopilotStepStatus.SKIPPED and not v:
            raise ValueError("Skipped step must provide a non-empty reason")
        return v

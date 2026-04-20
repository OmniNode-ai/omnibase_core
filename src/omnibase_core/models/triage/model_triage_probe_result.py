# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTriageProbeResult — outcome of invoking a single triage probe (OMN-9322)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_triage_probe_status import EnumProbeStatus
from omnibase_core.models.triage.model_triage_finding import ModelTriageFinding


class ModelTriageProbeResult(BaseModel):
    """Outcome of invoking a single triage probe.

    ERROR/TIMEOUT/SKIPPED states must still return a result (graceful degradation)
    so the orchestrator report surfaces every probe that ran, including failed ones.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    probe_name: str
    status: EnumProbeStatus
    findings: list[ModelTriageFinding] = Field(default_factory=list)
    duration_ms: int = Field(ge=0, description="Wall time of probe execution")
    error_message: str = Field(
        default="", description="Non-empty iff status in {ERROR, TIMEOUT}"
    )

    @model_validator(mode="after")
    def validate_error_message_contract(self) -> ModelTriageProbeResult:
        requires_error = self.status in {EnumProbeStatus.ERROR, EnumProbeStatus.TIMEOUT}
        has_error = bool(self.error_message.strip())
        if requires_error and not has_error:
            raise ValueError(
                "error_message is required when status is ERROR or TIMEOUT"
            )
        if not requires_error and has_error:
            raise ValueError(
                "error_message must be empty unless status is ERROR or TIMEOUT"
            )
        return self

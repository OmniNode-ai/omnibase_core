# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTriageProbeResult — outcome of invoking a single triage probe (OMN-9322)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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

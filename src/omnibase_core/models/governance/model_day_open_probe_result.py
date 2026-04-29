# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayOpenProbeResult — result from a single Phase 2 investigation probe."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_probe_status import EnumProbeStatus

_MAX_STRING_LENGTH = 10000


class ModelDayOpenProbeResult(BaseModel):
    """Result from a single Phase 2 investigation probe."""

    model_config = ConfigDict(frozen=True)

    probe_name: str = Field(
        ..., description="Probe identifier", max_length=_MAX_STRING_LENGTH
    )
    status: EnumProbeStatus = Field(..., description="Execution status of the probe")
    artifact_path: str | None = Field(
        default=None,
        description="Path to the probe's JSON artifact file",
        max_length=_MAX_STRING_LENGTH,
    )
    summary: str | None = Field(
        default=None,
        description="Brief summary of probe results",
        max_length=_MAX_STRING_LENGTH,
    )
    finding_count: int = Field(
        default=0, description="Number of findings from this probe", ge=0
    )
    error: str | None = Field(
        default=None,
        description="Error message if probe failed",
        max_length=_MAX_STRING_LENGTH,
    )
    duration_seconds: float = Field(
        default=0.0, description="Wall-clock duration of probe execution", ge=0.0
    )

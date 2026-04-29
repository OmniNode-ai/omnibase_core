# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelIntegrationProbeResult — result for a single integration surface probe."""

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.governance.enum_integration_surface import (
    EnumIntegrationSurface,
)
from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus
from omnibase_core.enums.governance.enum_probe_reason import EnumProbeReason

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_STRING_LENGTH = 10000


class ModelIntegrationProbeResult(BaseModel):
    """Result for a single integration surface probe."""

    model_config = ConfigDict(frozen=True)

    surface: EnumIntegrationSurface = Field(
        ..., description="The integration surface being probed"
    )
    status: EnumInvariantStatus = Field(
        ..., description="Probe result: PASS, FAIL, or UNKNOWN"
    )
    reason: EnumProbeReason | None = Field(
        default=None, description="Reason code when status is UNKNOWN"
    )
    detail: Annotated[str | None, Field(max_length=_MAX_STRING_LENGTH)] = Field(
        default=None, description="Human-readable detail about the probe outcome"
    )
    checked_at: str | None = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) when the probe was run. None if probe did not execute.",
        max_length=20,
    )

    @field_validator("checked_at")
    @classmethod
    def validate_checked_at(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _DATE_PATTERN.match(v):
            msg = f"Invalid date format: {v}. Expected ISO format (YYYY-MM-DD)"
            raise ValueError(msg)
        try:
            date.fromisoformat(v)
        except ValueError as e:
            msg = f"Invalid calendar date: {v}. {e!s}"
            raise ValueError(msg) from e
        return v

    @model_validator(mode="after")
    def validate_reason_consistency(self) -> "ModelIntegrationProbeResult":
        if self.status == EnumInvariantStatus.UNKNOWN and self.reason is None:
            msg = "reason is required when status is UNKNOWN"
            raise ValueError(msg)
        if self.status != EnumInvariantStatus.UNKNOWN and self.reason is not None:
            msg = "reason is only allowed when status is UNKNOWN"
            raise ValueError(msg)
        return self

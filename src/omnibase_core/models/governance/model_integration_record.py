# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelIntegrationRecord — aggregated /integration-sweep artifact."""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus
from omnibase_core.models.governance.model_integration_probe_result import (
    ModelIntegrationProbeResult,
)

# Basic SemVer (major.minor.patch only). Ported from onex_change_control.validation.patterns.
_SEMVER_PATTERN: re.Pattern[str] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 1000

__all__ = ["ModelIntegrationRecord", "ModelIntegrationProbeResult"]


class ModelIntegrationRecord(BaseModel):
    """Aggregated /integration-sweep artifact."""

    model_config = ConfigDict(frozen=True)

    # string-version-ok: YAML/JSON wire; format checked by field_validator
    schema_version: str = Field(
        ..., description="Schema version (SemVer format)", max_length=20
    )
    date: str = Field(..., description="ISO date (YYYY-MM-DD) of the sweep run")
    run_id: str = Field(
        ...,
        description="Unique identifier for this sweep run",
        max_length=_MAX_STRING_LENGTH,
    )
    tickets: list[ModelIntegrationProbeResult] = Field(
        default_factory=list,
        description="Per-surface probe results collected during this sweep",
        max_length=_MAX_LIST_ITEMS,
    )
    overall_status: EnumInvariantStatus = Field(
        default=EnumInvariantStatus.UNKNOWN,
        description="Derived sweep status. Computed by model_validator — do not set manually.",
    )

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if not _SEMVER_PATTERN.match(v):
            msg = f"Invalid schema_version format: {v}. Expected SemVer (e.g., '1.0.0')"
            raise ValueError(msg)
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
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
    def derive_overall_status(self) -> "ModelIntegrationRecord":
        statuses = [t.status for t in self.tickets]
        if not statuses:
            derived = EnumInvariantStatus.UNKNOWN
        elif any(s == EnumInvariantStatus.FAIL for s in statuses):
            derived = EnumInvariantStatus.FAIL
        elif all(s == EnumInvariantStatus.PASS for s in statuses):
            derived = EnumInvariantStatus.PASS
        else:
            derived = EnumInvariantStatus.UNKNOWN
        object.__setattr__(self, "overall_status", derived)
        return self

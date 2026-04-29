# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayOpen — daily morning investigation report model."""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.governance.model_day_open_finding import ModelDayOpenFinding
from omnibase_core.models.governance.model_day_open_infra_service import (
    ModelDayOpenInfraService,
)
from omnibase_core.models.governance.model_day_open_probe_result import (
    ModelDayOpenProbeResult,
)
from omnibase_core.models.governance.model_day_open_repo_sync_entry import (
    ModelDayOpenRepoSyncEntry,
)

# Basic SemVer (major.minor.patch only). Ported from onex_change_control.validation.patterns.
_SEMVER_PATTERN: re.Pattern[str] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MAX_LIST_ITEMS = 1000

__all__ = [
    "ModelDayOpen",
    "ModelDayOpenFinding",
    "ModelDayOpenInfraService",
    "ModelDayOpenProbeResult",
    "ModelDayOpenRepoSyncEntry",
]


class ModelDayOpen(BaseModel):
    """Daily morning investigation report model."""

    model_config = ConfigDict(frozen=True)

    # string-version-ok: YAML/JSON wire; format checked by field_validator
    schema_version: str = Field(
        ..., description="Schema version (SemVer format)", max_length=20
    )
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    run_id: str = Field(
        ..., description="Unique identifier for this begin-day run", max_length=1000
    )
    yesterday_corrections: list[str] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    repo_sync_status: list[ModelDayOpenRepoSyncEntry] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    infra_health: list[ModelDayOpenInfraService] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    probe_results: list[ModelDayOpenProbeResult] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    aggregated_findings: list[ModelDayOpenFinding] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    recommended_focus_areas: list[str] = Field(default_factory=list, max_length=10)
    total_duration_seconds: float = Field(
        default=0.0, description="Total wall-clock duration", ge=0.0
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

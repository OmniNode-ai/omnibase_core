# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayClose — daily close report model."""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.governance.model_day_close_actual_repo import (
    ModelDayCloseActualRepo,
)
from omnibase_core.models.governance.model_day_close_drift_detected import (
    ModelDayCloseDriftDetected,
)
from omnibase_core.models.governance.model_day_close_invariants_checked import (
    ModelDayCloseInvariantsChecked,
)
from omnibase_core.models.governance.model_day_close_plan_item import (
    ModelDayClosePlanItem,
)
from omnibase_core.models.governance.model_day_close_pr import ModelDayClosePR
from omnibase_core.models.governance.model_day_close_process_change import (
    ModelDayCloseProcessChange,
)
from omnibase_core.models.governance.model_day_close_risk import ModelDayCloseRisk

# Basic SemVer (major.minor.patch only). Ported from onex_change_control.validation.patterns.
_SEMVER_PATTERN: re.Pattern[str] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MAX_LIST_ITEMS = 1000

__all__ = [
    "ModelDayClose",
    "ModelDayCloseActualRepo",
    "ModelDayCloseDriftDetected",
    "ModelDayCloseInvariantsChecked",
    "ModelDayClosePR",
    "ModelDayClosePlanItem",
    "ModelDayCloseProcessChange",
    "ModelDayCloseRisk",
]


class ModelDayClose(BaseModel):
    """Daily close report model."""

    model_config = ConfigDict(frozen=True)

    # string-version-ok: YAML/JSON wire; format checked by field_validator
    schema_version: str = Field(
        ..., description="Schema version (SemVer format)", max_length=20
    )
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    process_changes_today: list[ModelDayCloseProcessChange] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    plan: list[ModelDayClosePlanItem] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    actual_by_repo: list[ModelDayCloseActualRepo] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    drift_detected: list[ModelDayCloseDriftDetected] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    invariants_checked: ModelDayCloseInvariantsChecked = Field(
        ..., description="Invariants checked status"
    )
    corrections_for_tomorrow: list[str] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    risks: list[ModelDayCloseRisk] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
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

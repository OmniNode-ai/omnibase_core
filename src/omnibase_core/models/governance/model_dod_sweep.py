# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodSweepResult — aggregate DoD sweep report."""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus
from omnibase_core.models.governance.model_dod_sweep_check_result import (
    ModelDodSweepCheckResult,
)
from omnibase_core.models.governance.model_dod_sweep_ticket_result import (
    ModelDodSweepTicketResult,
)

# Basic SemVer (major.minor.patch only). Ported from onex_change_control.validation.patterns.
_SEMVER_PATTERN: re.Pattern[str] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 1000

__all__ = [
    "ModelDodSweepResult",
    "ModelDodSweepCheckResult",
    "ModelDodSweepTicketResult",
]


class ModelDodSweepResult(BaseModel):
    """Aggregate DoD sweep report."""

    model_config = ConfigDict(frozen=True)

    # string-version-ok: YAML/JSON wire; format checked by field_validator
    schema_version: str = Field(
        ..., description="Schema version (SemVer)", max_length=20
    )
    date: str = Field(..., description="ISO date of sweep run")
    run_id: str = Field(
        ..., description="Unique sweep run identifier", max_length=_MAX_STRING_LENGTH
    )
    mode: Literal["batch", "targeted"] = Field(..., description="Sweep mode")
    lookback_days: int | None = Field(
        default=None, description="Look-back window for batch mode"
    )
    # string-id-ok: Linear epic/ticket ID for targeted mode (e.g., OMN-1234), not a DB UUID
    target_id: str | None = Field(
        default=None, description="Epic or ticket ID for targeted mode"
    )
    tickets: list[ModelDodSweepTicketResult] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    overall_status: EnumInvariantStatus = Field(default=EnumInvariantStatus.UNKNOWN)
    total_tickets: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    exempted: int = Field(default=0)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if not _SEMVER_PATTERN.match(v):
            msg = f"Invalid schema_version: {v}. Expected SemVer (e.g., '1.0.0')"
            raise ValueError(msg)
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not _DATE_PATTERN.match(v):
            msg = f"Invalid date format: {v}. Expected YYYY-MM-DD"
            raise ValueError(msg)
        date.fromisoformat(v)
        return v

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> "ModelDodSweepResult":
        if self.mode == "batch":
            if self.lookback_days is None:
                msg = "lookback_days is required for batch mode"
                raise ValueError(msg)
            if self.target_id is not None:
                msg = "target_id is only allowed for targeted mode"
                raise ValueError(msg)
        if self.mode == "targeted":
            if self.target_id is None:
                msg = "target_id is required for targeted mode"
                raise ValueError(msg)
            if self.lookback_days is not None:
                msg = "lookback_days is only allowed for batch mode"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def derive_aggregates(self) -> "ModelDodSweepResult":
        tickets = self.tickets
        passed = sum(
            1
            for t in tickets
            if t.overall_status == EnumInvariantStatus.PASS and not t.exempted
        )
        failed = sum(1 for t in tickets if t.overall_status == EnumInvariantStatus.FAIL)
        exempted_count = sum(1 for t in tickets if t.exempted)

        if failed > 0:
            derived = EnumInvariantStatus.FAIL
        elif passed > 0 and passed + exempted_count == len(tickets):
            derived = EnumInvariantStatus.PASS
        elif len(tickets) > 0 and exempted_count == len(tickets):
            derived = EnumInvariantStatus.UNKNOWN
        else:
            derived = EnumInvariantStatus.UNKNOWN

        object.__setattr__(self, "total_tickets", len(tickets))
        object.__setattr__(self, "passed", passed)
        object.__setattr__(self, "failed", failed)
        object.__setattr__(self, "exempted", exempted_count)
        object.__setattr__(self, "overall_status", derived)
        return self

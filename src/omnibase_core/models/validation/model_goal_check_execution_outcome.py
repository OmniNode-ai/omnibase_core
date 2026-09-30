# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, contract-owned pins for cross-repository goal evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)
from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType


class ModelGoalCheckExecutionOutcome(BaseModel):
    """Raw check outcome recorded in R before any trusted admission verdict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_id: str = Field(
        ..., min_length=1, max_length=128
    )  # string-id-ok: contract criterion key
    item_id: str = Field(
        ..., min_length=1, max_length=50
    )  # string-id-ok: contract DoD item key
    check_type: EnumDodCheckType
    check_value_sha256: str
    outcome: Literal["passed", "failed", "not_run"]
    evidence_sha256: str

    @field_validator("check_value_sha256", "evidence_sha256")
    @classmethod
    def _digests_are_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("check/evidence digest must use sha256:<64 lowercase hex>")
        return value

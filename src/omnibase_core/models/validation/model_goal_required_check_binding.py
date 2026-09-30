# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalRequiredCheckBinding."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)
from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType


class ModelGoalRequiredCheckBinding(BaseModel):
    """The protected check definition required to prove one criterion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str = Field(  # string-id-ok: contract DoD item key
        ..., min_length=1, max_length=50
    )
    check_type: EnumDodCheckType
    check_value_sha256: str

    @field_validator("check_value_sha256")
    @classmethod
    def _check_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("check digest must use sha256:<64 lowercase hex>")
        return value

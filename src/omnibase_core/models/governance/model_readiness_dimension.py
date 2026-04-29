# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelReadinessDimension — per-dimension readiness verdict with supporting evidence."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus

_MAX_STRING_LENGTH = 10000


class ModelReadinessDimension(BaseModel):
    """Per-dimension readiness verdict with supporting evidence."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Dimension name", max_length=_MAX_STRING_LENGTH)
    status: EnumDogfoodStatus = Field(..., description="PASS/WARN/FAIL/UNKNOWN verdict")
    evidence: str = Field(
        default="",
        description="Supporting evidence or failure reason",
        max_length=_MAX_STRING_LENGTH,
    )

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayClosePR — pull request entry in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_pr_state import EnumPRState

_MAX_STRING_LENGTH = 10000


class ModelDayClosePR(BaseModel):
    """Pull request entry in daily close report."""

    model_config = ConfigDict(frozen=True)

    pr: int = Field(..., description="PR number", ge=1)
    title: str = Field(..., description="PR title", max_length=_MAX_STRING_LENGTH)
    state: EnumPRState = Field(..., description="PR state")
    notes: str = Field(
        ...,
        description="Why it matters / what it unblocks",
        max_length=_MAX_STRING_LENGTH,
    )

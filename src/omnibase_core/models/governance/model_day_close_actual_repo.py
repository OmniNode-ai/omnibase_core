# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayCloseActualRepo — actual work by repository in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.governance.model_day_close_pr import ModelDayClosePR

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 1000


class ModelDayCloseActualRepo(BaseModel):
    """Actual work by repository in daily close report."""

    model_config = ConfigDict(frozen=True)

    repo: str = Field(..., description="Repository name", max_length=_MAX_STRING_LENGTH)
    prs: list[ModelDayClosePR] = Field(
        default_factory=list, description="List of PRs", max_length=_MAX_LIST_ITEMS
    )

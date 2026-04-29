# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayOpenRepoSyncEntry — repository sync status entry from Phase 1 pull-all."""

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelDayOpenRepoSyncEntry(BaseModel):
    """Repository sync status entry from Phase 1 pull-all."""

    model_config = ConfigDict(frozen=True)

    repo: str = Field(..., description="Repository name", max_length=_MAX_STRING_LENGTH)
    branch: str = Field(
        ..., description="Branch that was synced", max_length=_MAX_STRING_LENGTH
    )
    up_to_date: bool = Field(..., description="Whether the repo was already up to date")
    head_sha: str = Field(
        ..., description="HEAD commit SHA after sync", max_length=_MAX_STRING_LENGTH
    )
    error: str | None = Field(
        default=None,
        description="Error message if sync failed",
        max_length=_MAX_STRING_LENGTH,
    )

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output for repository-relative Git file listing."""

from pydantic import BaseModel, ConfigDict, Field


class ModelGitFileListingOutput(BaseModel):
    """Git paths, optional snapshot blobs, and revision/conflict evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    paths: list[str] = Field(default_factory=list)
    fell_back_to_all: bool = False
    revision_exists: bool | None = Field(
        default=None, description="Revision probe result, only for revision snapshots"
    )
    has_unmerged_entries: bool = False
    blobs: dict[str, bytes | None] = Field(default_factory=dict)

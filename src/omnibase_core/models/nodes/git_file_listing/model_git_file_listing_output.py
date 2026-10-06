# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output for repository-relative Git file listing."""

from pydantic import BaseModel, ConfigDict, Field


class ModelGitFileListingOutput(BaseModel):
    """NUL-delimited Git paths in Git order, retaining fallback evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    paths: list[str] = Field(default_factory=list)
    fell_back_to_all: bool = False

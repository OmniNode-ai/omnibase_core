# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input for repository-relative Git file listing."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelGitFileListingInput(BaseModel):
    """Select working-tree candidates or tracked index/revision snapshots.

    Snapshot mode overrides scope, skips gitlinks, and reads only blob_paths.
    Revision snapshots probe base_ref without falling back to working-tree files.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    root: Path
    scope: Literal["all", "diff"] = "all"
    base_ref: str = "origin/dev"
    snapshot: Literal["index", "revision"] | None = Field(
        default=None,
        description="When set, list only tracked snapshot paths; revision uses base_ref",
    )
    blob_paths: list[str] = Field(
        default_factory=list,
        description="Selected snapshot paths to read as bytes; absent paths return None",
    )

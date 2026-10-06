# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input for repository-relative Git file listing."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelGitFileListingInput(BaseModel):
    """Select all tracked/untracked files or changes against an explicit ref."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    root: Path
    scope: Literal["all", "diff"] = "all"
    base_ref: str = "origin/dev"

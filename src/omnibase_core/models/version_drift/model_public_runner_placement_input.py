# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the public-repository runner placement check (OMN-19998, OMN-21280)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelPublicRunnerPlacementInput"]


class ModelPublicRunnerPlacementInput(BaseModel):
    """A repository's workflow files and whether the repository is public.

    There is no baseline (OMN-21280): every self-hosted job of a public
    repository fails, and ``extra="forbid"`` refuses one passed in.

    Attributes:
        repository: The repository name the findings name.
        public: False means a private repository, where self-hosted runners are
            the rule and the check passes.
        files: Repository-relative (path, source) pairs of the workflows.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(min_length=1)
    public: bool = True
    files: tuple[ModelSourceFile, ...] = Field(default=())

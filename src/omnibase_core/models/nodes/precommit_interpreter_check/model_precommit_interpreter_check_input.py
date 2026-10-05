# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inline config and referenced shell sources for a pure interpreter check."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelPrecommitInterpreterCheckInput(BaseModel):
    """All source content is supplied by the caller, including shell scripts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config: ModelSourceFile
    scripts: list[ModelSourceFile] = Field(default_factory=list)
    repository_root: str | None = Field(
        default=None, description="Source-label root for absolute shell references."
    )

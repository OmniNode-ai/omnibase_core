# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input for the no-untyped-metadata COMPUTE node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelNoUntypedMetadataCheckInput(BaseModel):
    """Explicit source pairs to scan without filesystem access."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)

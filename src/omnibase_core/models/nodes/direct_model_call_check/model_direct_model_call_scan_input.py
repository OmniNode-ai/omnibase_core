# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallScanInput: the whole repository: the call graph needs every file at once (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_source_file import (
    ModelDirectModelCallSourceFile,
)

__all__ = ["ModelDirectModelCallScanInput"]


class ModelDirectModelCallScanInput(BaseModel):
    """The whole repository: the call graph needs every file at once."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository name, the key into sanctioned_packages")
    files: tuple[ModelDirectModelCallSourceFile, ...] = Field(
        description="Every scanned file of the repository"
    )

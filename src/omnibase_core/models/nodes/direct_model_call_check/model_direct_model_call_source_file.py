# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallSourceFile: one tracked file's text, already loaded by the EFFECT boundary (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDirectModelCallSourceFile"]


class ModelDirectModelCallSourceFile(BaseModel):
    """One tracked file's text, already loaded by the EFFECT boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative POSIX path")
    content: str = Field(description="Raw file text")

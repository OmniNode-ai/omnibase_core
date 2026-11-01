# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A fenced block read from a document by the diagram-drift check (OMN-21510)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDiagramBlock(BaseModel):
    """The language, body and fence positions of one fenced block."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    language: str = Field(description="Info string after the opening fence")
    body: tuple[str, ...] = Field(description="Lines between the fences")
    fence_index: int = Field(description="0-based line of the opening fence")
    end_index: int = Field(description="0-based line of the closing fence")

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire collapsed field model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWireCollapsedField(BaseModel):
    """A field collapsed into another field (e.g. into metadata)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Field name")
    note: str = Field(default="", description="Explanation of collapse")

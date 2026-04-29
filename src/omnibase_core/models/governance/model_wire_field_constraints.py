# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire field constraints model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWireFieldConstraints(BaseModel):
    """Optional constraints on a wire schema field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ge: float | None = Field(default=None, description="Greater than or equal to")
    le: float | None = Field(default=None, description="Less than or equal to")
    min_length: int | None = Field(default=None, description="Minimum string length")
    max_length: int | None = Field(default=None, description="Maximum string length")
    enum: list[str] | None = Field(default=None, description="Allowed enum values")

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File paths whose names are checked against the directory prefix rules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNamingConventionCheckInput(BaseModel):
    """File paths whose names are checked against the directory prefix rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    paths: tuple[str, ...] = Field(default_factory=tuple)

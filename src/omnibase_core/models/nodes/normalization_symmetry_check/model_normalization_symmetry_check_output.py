# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Normalization and schema symmetry finding messages."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNormalizationSymmetryCheckOutput(BaseModel):
    """Normalization and schema symmetry finding messages."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    messages: tuple[str, ...] = Field(default_factory=tuple)

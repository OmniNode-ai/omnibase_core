# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Literal-alias-duplicates-enum error messages across the supplied files."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLiteralDuplicationCheckOutput(BaseModel):
    """Literal-alias-duplicates-enum error messages across the supplied files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    errors: tuple[str, ...] = Field(default_factory=tuple)

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Enum member casing violation messages across the supplied files."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEnumMemberCasingCheckOutput(BaseModel):
    """Enum member casing violation messages across the supplied files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[str, ...] = Field(default_factory=tuple)

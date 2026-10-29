# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File naming convention violation messages for the supplied paths."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNamingConventionCheckOutput(BaseModel):
    """File naming convention violation messages for the supplied paths."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    errors: tuple[str, ...] = Field(default_factory=tuple)

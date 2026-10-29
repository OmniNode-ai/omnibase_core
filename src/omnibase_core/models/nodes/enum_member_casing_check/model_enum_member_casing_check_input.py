# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Source files whose enum member casing is checked, supplied as text."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelEnumMemberCasingCheckInput(BaseModel):
    """Source files whose enum member casing is checked, supplied as text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[ModelSourceFile, ...] = Field(default_factory=tuple)

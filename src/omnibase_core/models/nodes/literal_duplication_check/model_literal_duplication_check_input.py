# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Source files and known enum names for the Literal duplication check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelLiteralDuplicationCheckInput(BaseModel):
    """Source files and known enum names for the Literal duplication check."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[ModelSourceFile, ...] = Field(default_factory=tuple)
    known_enums: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Lowercase normalized enum names; empty means the built-in set.",
    )

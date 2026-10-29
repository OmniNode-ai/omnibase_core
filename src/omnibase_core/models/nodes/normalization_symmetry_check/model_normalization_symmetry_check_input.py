# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Source tree text scanned for producer/consumer normalization asymmetry."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelNormalizationSymmetryCheckInput(BaseModel):
    """Source tree text scanned for producer/consumer normalization asymmetry."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    root: str = Field(
        default="",
        description="Directory the file paths are relative to, for module-name derivation.",
    )
    files: tuple[ModelSourceFile, ...] = Field(default_factory=tuple)

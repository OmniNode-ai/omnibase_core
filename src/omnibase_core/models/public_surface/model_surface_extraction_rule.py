# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The extraction rule of one surface kind."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_public_surface_kind import EnumPublicSurfaceKind
from omnibase_core.models.public_surface.model_surface_extraction_source import (
    ModelSurfaceExtractionSource,
)


class ModelSurfaceExtractionRule(BaseModel):
    """One kind, one or more sources."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: EnumPublicSurfaceKind
    sources: tuple[ModelSurfaceExtractionSource, ...] = Field(min_length=1)

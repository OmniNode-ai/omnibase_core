# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A repository's dependency-direction baseline file (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dependency_direction.model_dependency_direction_baseline_entry import (
    ModelDependencyDirectionBaselineEntry,
)

__all__ = ["ModelDependencyDirectionBaseline"]


class ModelDependencyDirectionBaseline(BaseModel):
    """The pre-existing violations a repository records; the list only shrinks."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str | None = None
    violations: tuple[ModelDependencyDirectionBaselineEntry, ...] = Field(default=())

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the dependency_direction_check COMPUTE node (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dependency_direction.model_dependency_direction_baseline_entry import (
    ModelDependencyDirectionBaselineEntry,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_rules import (
    ModelDependencyDirectionRules,
)
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelDependencyDirectionCheckInput"]


class ModelDependencyDirectionCheckInput(BaseModel):
    """The scanned repository, the layer order, its files and its baseline.

    Attributes:
        repo: The repository being checked; must be declared in ``layer_map``.
        rules: Patterns, file classes and message templates (rows of
            ``dependency_direction.validation.yaml``).
        layer_map: The declared layer order.
        files: Repository-relative (path, source) pairs to scan.
        baseline: Pre-existing violations, reported as WARN instead of FAIL.
        report_stale_baseline: When True (a full-tree scan), a baseline entry
            no file produced any more is reported as WARN so it is removed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    rules: ModelDependencyDirectionRules
    layer_map: ModelRepoLayerMap
    files: tuple[ModelSourceFile, ...] = Field(default=())
    baseline: tuple[ModelDependencyDirectionBaselineEntry, ...] = Field(default=())
    report_stale_baseline: bool = False

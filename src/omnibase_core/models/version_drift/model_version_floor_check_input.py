# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the version-floor-ahead-of-consumers check (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.version_drift.model_consumer_pyproject import (
    ModelConsumerPyproject,
)

__all__ = ["ModelVersionFloorCheckInput"]


class ModelVersionFloorCheckInput(BaseModel):
    """The changed repository's pyproject at base and head, and every consumer's.

    Attributes:
        repo: The repository whose pull request is checked.
        layer_map: The registry (repositories and the distributions they publish).
        base_pyproject: The repository's pyproject.toml at the pull request base,
            or None when the base has none.
        head_pyproject: The repository's pyproject.toml at the head.
        consumers: Every other registry repository's pyproject as read at its
            origin default branch.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    layer_map: ModelRepoLayerMap
    base_pyproject: str | None = None
    head_pyproject: str
    consumers: tuple[ModelConsumerPyproject, ...] = Field(default=())

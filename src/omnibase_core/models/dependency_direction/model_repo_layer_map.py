# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The declared repository layer order (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dependency_direction.model_repo_layer import (
    ModelRepoLayer,
)

__all__ = ["ModelRepoLayerMap"]


class ModelRepoLayerMap(BaseModel):
    """Every repository's layer, loaded from ``contracts/repo_layers.yaml``.

    Attributes:
        github_org: The organisation that owns every repository in ``repos``;
            a workflow or clone reference is matched as ``<github_org>/<repo>``.
        repos: One entry per repository; repository names are unique.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    github_org: str = Field(min_length=1)
    repos: tuple[ModelRepoLayer, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_names(self) -> ModelRepoLayerMap:
        seen: set[str] = set()
        for entry in self.repos:
            names = {
                n.lower().replace("_", "-")
                for n in (entry.repo, *entry.python_modules, *entry.distributions)
            }
            clash = seen & names
            if clash:
                raise ValueError(
                    f"names {sorted(clash)} are declared by two repositories"
                )
            seen |= names
        return self

    def get(self, repo: str) -> ModelRepoLayer | None:
        """The entry for ``repo``, or None when the map does not declare it."""
        for entry in self.repos:
            if entry.repo == repo:
                return entry
        return None

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The dependency pin view of the downstream repository manifest (OMN-21478)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.version_drift.model_dependency_pin_repo import (
    ModelDependencyPinRepo,
)

__all__ = ["ModelDependencyPinManifest"]


class ModelDependencyPinManifest(BaseModel):
    """The downstream repository manifest."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    version: int
    repos: tuple[ModelDependencyPinRepo, ...]

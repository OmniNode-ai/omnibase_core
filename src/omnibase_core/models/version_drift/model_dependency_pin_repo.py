# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A downstream repository's dependency pin opt-in (OMN-21478)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.version_drift.model_dependency_pin import ModelDependencyPin
from omnibase_core.models.version_drift.model_dependency_pin_site import (
    ModelDependencyPinSite,
)

__all__ = ["ModelDependencyPinRepo"]


class ModelDependencyPinRepo(BaseModel):
    """A manifest repository: its handshake pin sites and dependency pin opt-in."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    pin_sites: tuple[ModelDependencyPinSite, ...] = ()
    notes: str | None = None
    dependency_pin: ModelDependencyPin | None = None

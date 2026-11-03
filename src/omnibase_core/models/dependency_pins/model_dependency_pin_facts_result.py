# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What the dependency-pin facts effect read (OMN-22360)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.dependency_pins.model_dependency_hook_history import (
    ModelDependencyHookHistory,
)
from omnibase_core.models.dependency_pins.model_dependency_release_inventory import (
    ModelDependencyReleaseInventory,
)

__all__ = ["ModelDependencyPinFactsResult"]


class ModelDependencyPinFactsResult(BaseModel):
    """Release inventories and hook histories, one per requested repository.

    Attributes:
        inventories: One per requested repository.
        hook_histories: One per bounded hook repository that has pins.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    inventories: tuple[ModelDependencyReleaseInventory, ...] = ()
    hook_histories: tuple[ModelDependencyHookHistory, ...] = ()

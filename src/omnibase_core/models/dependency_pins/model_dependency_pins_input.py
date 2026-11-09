# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The typed facts the pure dependency-pin checker judges (OMN-22360)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.dependency_pins.model_dependency_hook_history import (
    ModelDependencyHookHistory,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    ModelDependencyPinPolicy,
)
from omnibase_core.models.dependency_pins.model_dependency_release_inventory import (
    ModelDependencyReleaseInventory,
)

__all__ = ["ModelDependencyPinsInput"]


class ModelDependencyPinsInput(BaseModel):
    """One repository's manifests, the two overlays and the facts read for them.

    Attributes:
        manifest_path: Path of ``pyproject.toml`` as reported in findings.
        manifest_text: Its text.
        lock_path: Path of the lock file as reported in findings.
        lock_text: Its text, or ``None`` when the repository has no lock file.
        precommit_path: Path of ``.pre-commit-config.yaml`` as reported in findings.
        precommit_text: Its text, or ``None`` when the repository has none.
        repo: The repository when the manifest names no layer-map distribution.
        layer_map: The declared layer order.
        policy: The pin policy.
        inventories: Release inventories of the first-party dependencies.
        hook_histories: Histories of the bounded hook repositories.
        checked_on: The UTC day the check runs, which dates a hook revision exemption;
            with none, an exempted revision is judged as not exempt and the exemption
            reads as expired.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest_path: str = Field(min_length=1)
    manifest_text: str
    lock_path: str = Field(min_length=1)
    lock_text: str | None = None
    precommit_path: str = Field(min_length=1)
    precommit_text: str | None = None
    repo: str | None = None
    layer_map: ModelRepoLayerMap
    policy: ModelDependencyPinPolicy
    inventories: tuple[ModelDependencyReleaseInventory, ...] = ()
    hook_histories: tuple[ModelDependencyHookHistory, ...] = ()
    checked_on: date | None = None

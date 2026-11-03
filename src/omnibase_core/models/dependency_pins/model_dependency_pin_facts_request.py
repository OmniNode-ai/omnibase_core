# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What the dependency-pin facts effect is asked to read (OMN-22360)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    ModelDependencyPinPolicy,
)
from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin

__all__ = ["ModelDependencyPinFactsRequest"]


class ModelDependencyPinFactsRequest(BaseModel):
    """The repositories whose release tags, and the hook pins whose times, are needed.

    Attributes:
        github_org: The organisation of every repository (the layer map's).
        repos: Layer-map repositories whose release inventory is read.
        hook_pins: Pre-commit pins of a bounded hook repository.
        policy: The pin policy (tag pattern, URL template, hook repositories).
        hook_history_dir: An existing clone of the hook repository with its tags; when
            ``None`` the effect fetches the history itself.
        git_timeout_seconds: The limit of each git call.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    github_org: str = Field(min_length=1)
    repos: tuple[str, ...] = ()
    hook_pins: tuple[ModelPrecommitPin, ...] = ()
    policy: ModelDependencyPinPolicy
    hook_history_dir: str | None = None
    git_timeout_seconds: int = Field(gt=0)

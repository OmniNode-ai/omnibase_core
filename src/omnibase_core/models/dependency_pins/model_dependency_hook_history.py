# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Commit times of a hook repository's pinned revisions and release tags (OMN-22360)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)

__all__ = ["ModelDependencyHookHistory"]


class ModelDependencyHookHistory(BaseModel):
    """What the history of one hook repository says about the pinned revisions.

    Attributes:
        url: The hook repository URL as the pre-commit config names it.
        rev_times: The commit time of every pinned revision that resolved.
        release_times: The commit time of every release tag of the repository.
        error: Why the history could not be read; ``None`` when it was.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    url: str = Field(min_length=1)
    rev_times: tuple[ModelPrecommitRevTime, ...] = ()
    release_times: tuple[int, ...] = ()
    error: str | None = None

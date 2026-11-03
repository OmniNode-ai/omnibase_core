# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A pre-commit hook repository whose pinned revisions the policy bounds (OMN-22360)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyPinHookRepo"]


class ModelDependencyPinHookRepo(BaseModel):
    """The hook repository URL and the layer-map repository whose release tags measure it.

    Attributes:
        url: The ``repo:`` URL a ``.pre-commit-config.yaml`` entry names.
        repo: The layer-map repository that URL serves.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    url: str = Field(min_length=1)
    repo: str = Field(min_length=1)

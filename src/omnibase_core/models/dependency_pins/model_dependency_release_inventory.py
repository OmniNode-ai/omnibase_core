# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The release versions one repository has tagged (OMN-22360)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyReleaseInventory"]


class ModelDependencyReleaseInventory(BaseModel):
    """A repository's release versions, or why they could not be read.

    Attributes:
        repo: The layer-map repository.
        versions: Every version a release tag of the repository names.
        error: Why the inventory could not be read; ``None`` when it was.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    versions: tuple[str, ...] = ()
    error: str | None = None

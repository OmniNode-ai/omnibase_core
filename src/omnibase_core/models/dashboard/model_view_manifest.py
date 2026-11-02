# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelViewManifest — the views a pack publishes (OMN-21997)."""

from __future__ import annotations

from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dashboard.model_view_contract import ModelViewContract
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelViewManifest"]


class ModelViewManifest(BaseModel):
    """A versioned list of view contracts with unique view ids."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest_version: ModelSemVer = Field(..., description="Version of this manifest")
    views: tuple[ModelViewContract, ...] = Field(
        ..., min_length=1, description="View contracts"
    )

    @model_validator(mode="after")
    def validate_view_ids_are_distinct(self) -> Self:
        """Refuse two views with the same id.

        Raises:
            ValueError: If a view id appears more than once.
        """
        repeated = sorted(
            view_id
            for view_id, count in Counter(v.view_id for v in self.views).items()
            if count > 1
        )
        if repeated:
            raise ValueError(f"duplicate view ids: {repeated}")
        return self

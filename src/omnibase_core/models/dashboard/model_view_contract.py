# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelViewContract — a typed view, the shared layer surfaces render (OMN-21997)."""

from __future__ import annotations

from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dashboard.model_view_section_contract import (
    ModelViewSectionContract,
)
from omnibase_core.models.dashboard.model_view_slug import ViewSlug
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelViewContract"]


class ModelViewContract(BaseModel):
    """A view: a slug, a version and its sections."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    view_id: ViewSlug = Field(..., description="Slug of the view")
    title: str = Field(..., min_length=1, description="View title")
    contract_version: ModelSemVer = Field(
        ..., description="Version of this view contract"
    )
    sections: tuple[ModelViewSectionContract, ...] = Field(
        ..., min_length=1, description="Sections, in display order"
    )

    @model_validator(mode="after")
    def validate_section_ids_are_distinct(self) -> Self:
        """Refuse two sections with the same id.

        Raises:
            ValueError: If a section id appears more than once.
        """
        repeated = sorted(
            section_id
            for section_id, count in Counter(
                s.section_id for s in self.sections
            ).items()
            if count > 1
        )
        if repeated:
            raise ValueError(f"duplicate section ids: {repeated}")
        return self

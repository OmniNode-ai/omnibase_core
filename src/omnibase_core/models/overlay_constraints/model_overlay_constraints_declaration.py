# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ``overlay_constraints`` block of a contract (OMN-22185)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.overlay_constraints.model_overlay_relation import (
    ModelOverlayRelation,
)


class ModelOverlayConstraintsDeclaration(BaseModel):
    """Derived quantities and the relations that must hold between overlay keys."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    derived: dict[str, str] = Field(
        default_factory=dict,
        description="Derived name to the sum of keys or numbers it stands for",
    )
    relations: tuple[ModelOverlayRelation, ...] = Field(
        min_length=1, description="Relations that must all hold"
    )

    @model_validator(mode="after")
    def _relation_names_are_unique(self) -> ModelOverlayConstraintsDeclaration:
        ids = [relation.relation_name for relation in self.relations]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate relation ids: {duplicates}")
        return self

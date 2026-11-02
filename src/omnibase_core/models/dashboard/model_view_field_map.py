# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelViewFieldMap — how an exposure's columns fill a row model (OMN-21997).

Typed row selection plus one binding per row-model field. Sources are column
names, constants and references; there is no expression language, so a derived
value is computed upstream in the exposure and arrives as a column.
"""

from __future__ import annotations

from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dashboard.model_view_field_binding import (
    ModelViewFieldBinding,
)
from omnibase_core.models.dashboard.model_view_row_selection import (
    ModelViewRowSelection,
)

__all__ = ["ModelViewFieldMap"]


class ModelViewFieldMap(BaseModel):
    """Row selection and field bindings for one section."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    selection: ModelViewRowSelection = Field(
        ..., description="Exposure, unique key, ordering and limit"
    )
    fields: tuple[ModelViewFieldBinding, ...] = Field(
        ..., min_length=1, description="One binding per row-model field"
    )

    @model_validator(mode="after")
    def validate_targets_are_distinct(self) -> Self:
        """Refuse two bindings for the same row-model field.

        Raises:
            ValueError: If a target appears more than once.
        """
        repeated = sorted(
            target
            for target, count in Counter(f.target for f in self.fields).items()
            if count > 1
        )
        if repeated:
            raise ValueError(f"duplicate field targets: {repeated}")
        return self

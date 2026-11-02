# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed row selection of a view section (OMN-21997).

A selection names an exposure, the columns of that exposure's declared unique
key, an ordering and a limit. The ordering decides display order only: a row's
identity is its unique-key values, never its position (plan §10.1).
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dashboard.model_view_column_name import ViewColumnName
from omnibase_core.models.dashboard.model_view_order_column import ModelViewOrderColumn

__all__ = ["ModelViewRowSelection"]


class ModelViewRowSelection(BaseModel):
    """Which rows of which exposure a section shows."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    exposure: ViewColumnName = Field(
        ..., description="Name of the exposure the rows are read from"
    )
    unique_key: tuple[ViewColumnName, ...] = Field(
        ...,
        min_length=1,
        description="Columns of the exposure's declared unique key; they form the row id",
    )
    order_by: tuple[ModelViewOrderColumn, ...] = Field(
        default=(), description="Display ordering; never part of a row's identity"
    )
    limit: int | None = Field(
        default=None, ge=1, le=10000, description="Maximum number of rows"
    )

    @model_validator(mode="after")
    def validate_unique_key_columns_are_distinct(self) -> Self:
        """Refuse a unique key that names a column twice.

        Raises:
            ValueError: If a unique-key column is repeated.
        """
        if len(set(self.unique_key)) != len(self.unique_key):
            raise ValueError("unique_key must not repeat a column")
        return self

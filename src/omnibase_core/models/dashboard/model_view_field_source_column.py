# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Field source: a column of the exposure (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_column_name import ViewColumnName

__all__ = ["ModelViewFieldSourceColumn"]


class ModelViewFieldSourceColumn(BaseModel):
    """Take the value from a named column, unchanged."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_kind: Literal["column"] = Field(
        default="column", description="Discriminator for the field source union"
    )
    column: ViewColumnName = Field(..., description="Column name, never an expression")

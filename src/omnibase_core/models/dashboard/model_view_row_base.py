# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Base for the row models of the view kinds (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_row_id import ModelViewRowId

__all__ = ["ModelViewRowBase"]


class ModelViewRowBase(BaseModel):
    """A row of a view section. Every kind's row carries a typed row id."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    row_id: ModelViewRowId = Field(
        ...,
        description="View id, section id and declared unique-key values of this row",
    )

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section and row ids of one disposition (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_view_disposition import EnumViewDisposition

__all__ = ["ModelViewDispositionCount"]


class ModelViewDispositionCount(BaseModel):
    """The sections of a document in one disposition and their row ids."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    disposition: EnumViewDisposition = Field(..., description="The disposition")
    section_ids: tuple[str, ...] = Field(
        ..., description="Ids of the sections in this disposition, document order"
    )
    row_ids: tuple[str, ...] = Field(
        ..., description="Rendered ids of those sections' rows, document order"
    )

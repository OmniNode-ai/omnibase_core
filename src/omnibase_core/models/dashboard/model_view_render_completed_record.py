# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A completed view render and the content the app drew (OMN-21999).

The disposition carries a typed empty-state cause when needed. Drawn section
and row identifiers are unique within each tuple; a refusal draws neither.
"""

from __future__ import annotations

from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_view_render_disposition import EnumViewRenderDisposition
from omnibase_core.models.dashboard.model_view_id_patterns import ViewId

__all__ = ["ModelViewRenderCompletedRecord"]


class ModelViewRenderCompletedRecord(BaseModel):
    """Completion time, disposition, cause and identifiers actually drawn.

    A drawn view has no cause unless its disposition explicitly says so. A
    refused view requires a cause and cannot claim any drawn sections or rows.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    completed_at: AwareDatetime = Field(
        ..., description="Time the app completed the render attempt"
    )
    disposition: EnumViewRenderDisposition = Field(
        ..., description="Disposition of the completed render attempt"
    )
    cause: EnumEmptyStateReason | None = Field(
        default=None, description="Empty-state reason for a partial render or refusal"
    )
    section_ids_drawn: tuple[ViewId, ...] = Field(
        default=(), description="Unique identifiers of sections actually drawn"
    )
    row_ids_drawn: tuple[ViewId, ...] = Field(
        default=(), description="Unique identifiers of rows actually drawn"
    )

    @model_validator(mode="after")
    def validate_render_result(self) -> Self:
        """Enforce cause, refusal and drawn identifier invariants.

        Raises:
            ValueError: If the cause disagrees with the disposition, a refusal
                claims drawn content, or either identifier tuple has duplicates.
        """
        if self.disposition == EnumViewRenderDisposition.DRAWN:
            if self.cause is not None:
                raise ValueError("drawn requires cause to be None")
        elif self.cause is None:
            raise ValueError("drawn-with-cause and refused require cause")
        if self.disposition == EnumViewRenderDisposition.REFUSED and (
            self.section_ids_drawn or self.row_ids_drawn
        ):
            raise ValueError(
                "refused requires empty section_ids_drawn and row_ids_drawn"
            )
        if len(self.section_ids_drawn) != len(set(self.section_ids_drawn)):
            raise ValueError("section_ids_drawn must not contain duplicates")
        if len(self.row_ids_drawn) != len(set(self.row_ids_drawn)):
            raise ValueError("row_ids_drawn must not contain duplicates")
        return self

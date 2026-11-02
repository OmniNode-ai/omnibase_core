# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One ordering column of a row selection (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_binding_order_direction import EnumBindingOrderDirection
from omnibase_core.models.dashboard.model_view_column_name import ViewColumnName

__all__ = ["ModelViewOrderColumn"]


class ModelViewOrderColumn(BaseModel):
    """A column and the direction rows are ordered by it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    column: ViewColumnName = Field(..., description="Column to order by")
    direction: EnumBindingOrderDirection = Field(
        default=EnumBindingOrderDirection.ASCENDING, description="Order direction"
    )

# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Table column configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelTableColumnConfig"]


class ModelTableColumnConfig(BaseModel):
    """Configuration for a single table column."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    key: str = Field(..., description="Data key for this column")
    header: str = Field(..., description="Column header display text")
    width: int | None = Field(default=None, description="Column width in pixels")
    sortable: bool = Field(default=True, description="Allow sorting by this column")
    align: Literal["left", "center", "right"] = Field(
        default="left", description="Text alignment"
    )
    format: str | None = Field(
        default=None, description="Display format (e.g., 'currency', 'percent', 'date')"
    )

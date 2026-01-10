# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Table widget configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_table_column_config import (
    ModelTableColumnConfig,
)

__all__ = ["ModelWidgetConfigTable"]


class ModelWidgetConfigTable(BaseModel):
    """Table widget configuration.

    Defines how a table widget displays tabular data with columns.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_kind: Literal["table"] = Field(
        default="table", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.TABLE, description="Widget type enum value"
    )
    columns: tuple[ModelTableColumnConfig, ...] = Field(
        default=(), description="Table column configurations"
    )
    page_size: int = Field(default=10, ge=1, le=100, description="Rows per page")
    show_pagination: bool = Field(default=True, description="Show pagination controls")
    default_sort_key: str | None = Field(
        default=None, description="Default column key to sort by"
    )
    default_sort_direction: Literal["asc", "desc"] = Field(
        default="asc", description="Default sort direction"
    )
    striped: bool = Field(default=True, description="Alternate row colors")
    hover_highlight: bool = Field(default=True, description="Highlight row on hover")

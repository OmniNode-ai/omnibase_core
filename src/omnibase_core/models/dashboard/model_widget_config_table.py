"""Table widget configuration model.

This module defines the configuration for table-based dashboard widgets,
supporting paginated, sortable, and styled tabular data display with
customizable columns.

Example:
    Create a sortable table with pagination::

        from omnibase_core.models.dashboard import (
            ModelWidgetConfigTable,
            ModelTableColumnConfig,
        )

        config = ModelWidgetConfigTable(
            columns=(
                ModelTableColumnConfig(key="name", header="Name", sortable=True),
                ModelTableColumnConfig(key="status", header="Status", align="center"),
                ModelTableColumnConfig(key="count", header="Count", align="right"),
            ),
            page_size=25,
            default_sort_key="name",
            default_sort_direction="asc",
        )
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_table_column_config import (
    ModelTableColumnConfig,
)

__all__ = ("ModelWidgetConfigTable",)

#: Expected config_kind value for this widget type.
_EXPECTED_CONFIG_KIND = "table"


class ModelWidgetConfigTable(BaseModel):
    """Configuration for table-type dashboard widgets.

    Defines how a table widget displays tabular data with configurable
    columns, pagination, sorting, and visual styling options. Tables
    support client-side sorting and pagination with customizable page sizes.

    Attributes:
        config_kind: Literal discriminator value, always "table".
        widget_type: Widget type enum, always TABLE.
        columns: Tuple of column configurations defining table structure.
        page_size: Number of rows displayed per page (1-100).
        show_pagination: Whether to show pagination controls.
        default_sort_key: Column key to sort by initially, or None.
        default_sort_direction: Sort direction ("asc" or "desc"). Only valid
            when default_sort_key is set.
        striped: Whether to alternate row background colors.
        hover_highlight: Whether to highlight rows on mouse hover.

    Raises:
        ValueError: If default_sort_direction is set without default_sort_key.

    Example:
        Compact table without pagination::

            config = ModelWidgetConfigTable(
                columns=(col1, col2),
                page_size=100,
                show_pagination=False,
                striped=False,
            )
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
    default_sort_direction: Literal["asc", "desc"] | None = Field(
        default=None,
        description="Default sort direction (only used when default_sort_key is set)",
    )
    striped: bool = Field(default=True, description="Alternate row colors")
    hover_highlight: bool = Field(default=True, description="Highlight row on hover")

    @model_validator(mode="after")
    def validate_sort_direction(self) -> Self:
        """Validate sort direction is only set when sort key is set."""
        if self.default_sort_direction is not None and self.default_sort_key is None:
            raise ValueError(
                "default_sort_direction can only be set when default_sort_key is specified"
            )
        return self

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type is consistent with config_kind.

        Ensures that the widget_type enum matches the expected config_kind
        discriminator value. widget_type=TABLE must have config_kind="table".

        Raises:
            ValueError: If widget_type does not match config_kind.
        """
        if self.widget_type is not EnumWidgetType.TABLE:
            raise ValueError(
                f"widget_type must be TABLE for table config, got {self.widget_type.value}"
            )
        if self.config_kind != _EXPECTED_CONFIG_KIND:
            raise ValueError(
                f"config_kind must be '{_EXPECTED_CONFIG_KIND}' for TABLE widget, "
                f"got '{self.config_kind}'"
            )
        return self

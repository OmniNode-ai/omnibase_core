"""Table column configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ("ModelTableColumnConfig",)


class ModelTableColumnConfig(BaseModel):
    """Configuration for a single column in dashboard table widgets.

    Defines column display properties including header text, width,
    sorting behavior, alignment, and value formatting.

    Used by table-based dashboard widgets to configure column rendering
    and user interaction capabilities.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, populate_by_name=True
    )

    key: str = Field(..., min_length=1, description="Data key for this column")
    header: str = Field(..., min_length=1, description="Column header display text")
    width: int | None = Field(
        default=None, ge=1, description="Column width in pixels (minimum 1 when set)"
    )
    sortable: bool = Field(default=True, description="Allow sorting by this column")
    align: Literal["left", "center", "right"] = Field(
        default="left", description="Text alignment"
    )
    display_format: str | None = Field(
        default=None,
        alias="format",
        description="Display format (e.g., 'currency', 'percent', 'date')",
    )

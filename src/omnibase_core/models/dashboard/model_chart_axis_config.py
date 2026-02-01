"""Chart axis configuration model."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ("ModelChartAxisConfig",)


class ModelChartAxisConfig(BaseModel):
    """Configuration for a chart axis in dashboard visualizations.

    Defines display properties for X or Y axes in chart widgets,
    including labels, value ranges, and grid visibility.

    Used by chart-based dashboard widgets to configure axis rendering.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    label: str | None = Field(default=None, description="Axis label")
    min_value: float | None = Field(default=None, description="Minimum axis value")
    max_value: float | None = Field(default=None, description="Maximum axis value")
    show_grid: bool = Field(default=True, description="Show grid lines")

    @model_validator(mode="after")
    def validate_min_less_than_max(self) -> Self:
        """Validate that min_value is less than max_value when both are set."""
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value >= self.max_value
        ):
            raise ValueError(
                f"min_value ({self.min_value}) must be less than max_value ({self.max_value})"
            )
        return self

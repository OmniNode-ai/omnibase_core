# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Chart series configuration model."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ("ModelChartSeriesConfig",)

# Internal pattern for valid hex color formats: #RGB, #RRGGBB, #RGBA, #RRGGBBAA
_HEX_COLOR_PATTERN = re.compile(
    r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{8})$"
)


class ModelChartSeriesConfig(BaseModel):
    """Configuration for a single data series in dashboard charts.

    Defines how a dataset should be rendered within a chart widget,
    including the data source key, visual styling, and chart type.

    Multiple series configs can be combined to create multi-series
    charts with different visualization styles (line, bar, area, scatter).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., min_length=1, description="Series display name")
    data_key: str = Field(
        ..., min_length=1, description="Key to extract data from source"
    )
    color: str | None = Field(default=None, description="Series color (hex)")
    series_type: Literal["line", "bar", "area", "scatter"] = Field(
        default="line", description="How to render this series"
    )

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        """Validate that color is a valid hex color code when provided."""
        if v is not None and not _HEX_COLOR_PATTERN.match(v):
            raise ValueError(
                f"Invalid hex color format: {v}. "
                "Expected #RGB, #RRGGBB, #RGBA, or #RRGGBBAA"
            )
        return v

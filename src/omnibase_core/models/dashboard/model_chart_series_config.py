# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Chart series configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelChartSeriesConfig"]


class ModelChartSeriesConfig(BaseModel):
    """Configuration for a single data series in dashboard charts.

    Defines how a dataset should be rendered within a chart widget,
    including the data source key, visual styling, and chart type.

    Multiple series configs can be combined to create multi-series
    charts with different visualization styles (line, bar, area, scatter).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., description="Series display name")
    data_key: str = Field(..., description="Key to extract data from source")
    color: str | None = Field(default=None, description="Series color (hex)")
    series_type: Literal["line", "bar", "area", "scatter"] = Field(
        default="line", description="How to render this series"
    )

# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Chart axis configuration model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelChartAxisConfig"]


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

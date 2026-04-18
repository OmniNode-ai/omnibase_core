# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Optional dashboard presentation hint for a projector contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_dashboard_widget_type import EnumDashboardWidgetType


class ModelDashboardHint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    widget_type: EnumDashboardWidgetType = Field(
        ..., description="Preferred widget shape."
    )
    label: str | None = Field(default=None, description="Human-readable label.")
    group: str | None = Field(
        default=None, description="Grouping key for sidebar organization."
    )
    priority: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Ordering weight; lower renders first.",
    )
    time_series: bool = Field(
        default=False, description="Treat as time-series if True."
    )
    unit: str | None = Field(
        default=None, description="Units annotation (e.g. 'usd', 'ms')."
    )

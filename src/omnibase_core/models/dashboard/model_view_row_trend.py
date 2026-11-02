# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``trend`` section (OMN-21997)."""

from __future__ import annotations

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase
from omnibase_core.models.dashboard.model_view_trend_point import ModelViewTrendPoint

__all__ = ["ModelViewRowTrend"]


class ModelViewRowTrend(ModelViewRowBase):
    """A series of timestamped values for one measure."""

    label: str = Field(..., min_length=1, description="Measure label")
    points: tuple[ModelViewTrendPoint, ...] = Field(
        ..., min_length=1, description="Timestamped values, in display order"
    )
    unit: str | None = Field(
        default=None, min_length=1, description="Unit of the values"
    )

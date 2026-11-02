# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``trend`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_trend import (
    ModelViewRowTrend,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionTrend"]


class ModelViewSectionTrend(ModelViewSectionBase):
    """A ``trend`` section: trend rows under a trend envelope."""

    kind: Literal["trend"] = Field(
        default="trend", description="View kind; the document union discriminator"
    )
    rows: tuple[ModelViewRowTrend, ...] = Field(
        default=(), description="Trend rows; empty when empty_state is set"
    )

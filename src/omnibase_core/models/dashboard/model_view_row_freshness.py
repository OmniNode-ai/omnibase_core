# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``freshness`` section (OMN-21997)."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase

__all__ = ["ModelViewRowFreshness"]


class ModelViewRowFreshness(ModelViewRowBase):
    """How old a feed's last observation is against its allowance."""

    label: str = Field(..., min_length=1, description="Feed label")
    observed_at: AwareDatetime | None = Field(
        ..., description="When the feed was last observed; None if never"
    )
    max_age_seconds: int = Field(
        ..., gt=0, description="Allowed age of the last observation, in seconds"
    )
    severity: EnumStatusSeverity = Field(..., description="Upstream severity verdict")

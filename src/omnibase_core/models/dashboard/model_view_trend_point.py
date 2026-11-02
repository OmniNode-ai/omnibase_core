# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One timestamped value of a trend row (OMN-21997)."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

__all__ = ["ModelViewTrendPoint"]


class ModelViewTrendPoint(BaseModel):
    """A value at a moment."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    at: AwareDatetime = Field(..., description="When the value was observed")
    value: float = Field(..., allow_inf_nan=False, description="Observed value")

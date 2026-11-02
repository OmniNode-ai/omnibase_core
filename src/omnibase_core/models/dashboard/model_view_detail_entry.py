# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One labelled entry of a drawer-detail row (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelViewDetailEntry"]


class ModelViewDetailEntry(BaseModel):
    """A label and its value."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    label: str = Field(..., min_length=1, description="What the value is")
    value: str = Field(..., description="The value, already formatted for display")

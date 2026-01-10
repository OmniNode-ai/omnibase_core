# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Status item configuration model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelStatusItemConfig"]


class ModelStatusItemConfig(BaseModel):
    """Configuration for a status indicator in dashboard status grids.

    Defines display properties for individual status items, including
    the data key to monitor, display label, and optional icon.

    Used by status grid widgets to render system health indicators,
    metrics summaries, and key-value status displays.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    key: str = Field(..., description="Data key for this status item")
    label: str = Field(..., description="Display label")
    icon: str | None = Field(default=None, description="Icon identifier")

# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard layout configuration model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDashboardLayoutConfig"]


class ModelDashboardLayoutConfig(BaseModel):
    """Dashboard layout configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    columns: int = Field(default=12, ge=1, le=24, description="Grid column count")
    row_height: int = Field(default=100, ge=50, description="Row height in pixels")
    gap: int = Field(default=16, ge=0, description="Gap between widgets in pixels")
    responsive: bool = Field(default=True, description="Enable responsive layout")

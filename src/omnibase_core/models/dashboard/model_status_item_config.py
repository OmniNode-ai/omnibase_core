# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Status item configuration model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelStatusItemConfig"]


class ModelStatusItemConfig(BaseModel):
    """Configuration for a single status item in the grid."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    key: str = Field(..., description="Data key for this status item")
    label: str = Field(..., description="Display label")
    icon: str | None = Field(default=None, description="Icon identifier")

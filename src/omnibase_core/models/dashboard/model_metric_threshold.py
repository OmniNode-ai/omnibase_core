# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Metric threshold configuration model."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelMetricThreshold"]

# Pattern for valid hex color formats: #RGB, #RRGGBB, #RGBA, #RRGGBBAA
HEX_COLOR_PATTERN = re.compile(
    r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{8})$"
)


class ModelMetricThreshold(BaseModel):
    """Threshold configuration for metric display."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(..., description="Threshold value")
    color: str = Field(..., description="Color when threshold is reached (hex)")
    label: str | None = Field(default=None, description="Threshold label")

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate that color is a valid hex color code."""
        if not HEX_COLOR_PATTERN.match(v):
            raise ValueError(
                f"Invalid hex color format: {v}. "
                "Expected #RGB, #RRGGBB, #RGBA, or #RRGGBBAA"
            )
        return v

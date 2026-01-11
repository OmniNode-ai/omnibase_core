# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Metric threshold configuration model.

This module defines the threshold configuration used in metric card widgets
to apply conditional coloring based on metric values. Thresholds enable
visual indicators for normal, warning, and critical states.

Example:
    Define thresholds for a response time metric::

        from omnibase_core.models.dashboard import ModelMetricThreshold

        thresholds = (
            ModelMetricThreshold(value=100, color="#22c55e", label="Fast"),
            ModelMetricThreshold(value=500, color="#eab308", label="Slow"),
            ModelMetricThreshold(value=1000, color="#ef4444", label="Critical"),
        )
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ("ModelMetricThreshold",)

# Internal pattern for valid hex color formats: #RGB, #RRGGBB, #RGBA, #RRGGBBAA
_HEX_COLOR_PATTERN = re.compile(
    r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{8})$"
)


class ModelMetricThreshold(BaseModel):
    """Threshold configuration for conditional metric coloring.

    Defines a value threshold that triggers a color change in metric card
    widgets. Multiple thresholds can be configured to create a color scale
    (e.g., green -> yellow -> red) based on the metric value.

    Thresholds are typically evaluated in ascending order by value. When
    the metric exceeds a threshold value, that threshold's color is applied.

    Attributes:
        value: The numeric threshold value. When the metric reaches or
            exceeds this value, the associated color is applied.
        color: Hex color code to apply when threshold is reached. Must be
            a valid hex format (#RGB, #RRGGBB, #RGBA, or #RRGGBBAA).
        label: Optional human-readable label for the threshold level
            (e.g., "Good", "Warning", "Critical").

    Raises:
        ValueError: If color is not a valid hex color format.

    Example:
        Single warning threshold::

            threshold = ModelMetricThreshold(
                value=80.0,
                color="#eab308",
                label="High Usage",
            )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(..., description="Threshold value")
    color: str = Field(..., description="Color when threshold is reached (hex)")
    label: str | None = Field(default=None, description="Threshold label")

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate that color is a valid hex color code."""
        if not _HEX_COLOR_PATTERN.match(v):
            raise ValueError(
                f"Invalid hex color format: {v}. "
                "Expected #RGB, #RRGGBB, #RGBA, or #RRGGBBAA"
            )
        return v

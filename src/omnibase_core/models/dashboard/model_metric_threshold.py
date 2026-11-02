# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Metric threshold configuration model.

This module defines the threshold configuration used in metric card widgets
to apply conditional coloring based on metric values. Thresholds enable
visual indicators for normal, warning, and critical states.

Example:
    Define thresholds for a response time metric::

        from omnibase_core.models.dashboard import ModelMetricThreshold

        thresholds = (
            ModelMetricThreshold(
                value=100, color="color_status_success", label="Fast"
            ),
            ModelMetricThreshold(
                value=500, color="color_status_warning", label="Slow"
            ),
            ModelMetricThreshold(
                value=1000, color="color_status_error", label="Critical"
            ),
        )
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.dashboard.model_renderer_theme_contract import (
    ModelRendererThemeContract,
)

__all__ = ("ModelMetricThreshold",)


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
        color: Name of the ModelRendererThemeContract colour token to apply
            when the threshold is reached (e.g. "color_status_warning"). A
            NAME, never a colour value.
        label: Optional human-readable label for the threshold level
            (e.g., "Good", "Warning", "Critical").

    Raises:
        ValueError: If color is not a colour token of the theme contract.

    Example:
        Single warning threshold::

            threshold = ModelMetricThreshold(
                value=80.0,
                color="color_status_warning",
                label="High Usage",
            )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(..., description="Threshold value")
    color: str = Field(
        ...,
        description=(
            "Name of the ModelRendererThemeContract colour token applied when the "
            "threshold is reached (e.g. 'color_status_warning'). A NAME, never a "
            "colour value."
        ),
    )
    label: str | None = Field(default=None, description="Threshold label")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate that color names a theme colour token.

        Raises:
            ValueError: If ``v`` is not a colour token of the theme contract.
        """
        if not ModelRendererThemeContract.is_color_token_name(v):
            raise ValueError(
                f"'{v}' is not a colour token of ModelRendererThemeContract; a "
                f"colour field must name a theme token (e.g. 'color_accent_primary'), "
                f"and a colour value is never accepted"
            )
        return v

# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Metric threshold configuration model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelMetricThreshold"]


class ModelMetricThreshold(BaseModel):
    """Threshold configuration for metric display."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(..., description="Threshold value")
    color: str = Field(..., description="Color when threshold is reached (hex)")
    label: str | None = Field(default=None, description="Threshold label")

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed numeric score for the Shared Experiment Result Contract (OMN-13613).

A bare float is ambiguous about its scale; pairing the value with an explicit
``scale_max`` makes "0.875 out of 1.0" unambiguous across the three Phase-3
experiment orchestrators of the SEA→canonical migration (epic OMN-13604).

.. versionadded:: OMN-13613
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelExperimentScore"]


class ModelExperimentScore(BaseModel):
    """Typed numeric score for an experiment result."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(
        ...,
        ge=0.0,
        description="Measured score, in the range [0.0, scale_max].",
    )
    scale_max: float = Field(
        default=1.0,
        gt=0.0,
        description="Maximum possible score on this scale (default 1.0).",
    )

    @model_validator(mode="after")
    def _validate_value_within_scale(self) -> ModelExperimentScore:
        if self.value > self.scale_max:
            raise ValueError(
                f"score value {self.value} exceeds scale_max {self.scale_max}"
            )
        return self

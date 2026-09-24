# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hourly cost policy for one accelerator type (OMN-19391).

Ported from infra ``models/pricing/model_compute_cost_entry.py`` so that the
``llm.pricing`` overlay can replace infra's whole pricing manifest (plan C2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLlmComputeCostEntry(BaseModel):
    """Electricity and amortization cost per accelerator hour."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    electricity_per_hour: float = Field(
        ..., ge=0.0, description="Electricity cost per accelerator hour."
    )
    amortization_per_hour: float = Field(
        ..., ge=0.0, description="Hardware amortization per accelerator hour."
    )
    note: str = Field(default="", max_length=512, description="Free-form note.")

    @property
    def total_per_hour(self) -> float:
        """Combined hourly rate."""
        return self.electricity_per_hour + self.amortization_per_hour


__all__ = ["ModelLlmComputeCostEntry"]

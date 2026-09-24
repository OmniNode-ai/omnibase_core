# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence behind a measured ``llm.pricing`` entry (OMN-19391).

Ported from the ``evidence`` mapping of infra's pricing manifest, typed.
"""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ModelLlmPricingEvidence(BaseModel):
    """The usage sample a measured price was computed from."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    generated_at: AwareDatetime = Field(
        ..., description="When the price was computed (timezone-aware)."
    )
    sample_window_days: int = Field(
        ..., ge=1, description="Days of usage rows the sample covers."
    )
    sample_count: int = Field(..., ge=0, description="Usage rows in the sample.")
    min_samples: int = Field(
        ..., ge=0, description="Rows required before the price is authoritative."
    )
    query: str = Field(
        ..., min_length=1, max_length=1024, description="How the rows were selected."
    )
    authoritative: bool = Field(
        ..., description="True when the sample met min_samples."
    )


__all__ = ["ModelLlmPricingEvidence"]

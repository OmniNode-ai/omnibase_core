# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ``llm.pricing`` overlay document body (OMN-19391).

The typed replacement for infra's ``configs/pricing_manifest.yaml`` (plan C2)
and the pricing file omniclaude hooks read (plan E3). No field defaults to a
price: ``models`` is required, and the optional compute and runner sections
default to absent, never to a rate.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.config_overlay.model_llm_compute_cost_entry import (
    ModelLlmComputeCostEntry,
)
from omnibase_core.models.config_overlay.model_llm_pricing_entry import (
    ModelLlmPricingEntry,
)
from omnibase_core.models.config_overlay.model_llm_runner_cost_policy import (
    ModelLlmRunnerCostPolicy,
)


class ModelLlmPricingOverlay(BaseModel):
    """Model key to price, plus accelerator and runner cost policies."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["llm_pricing.v1"] = Field(
        ..., description="Schema version tag."
    )
    models: dict[str, ModelLlmPricingEntry] = Field(
        ..., description="Logical model key to its price."
    )
    compute_cost: dict[str, ModelLlmComputeCostEntry] = Field(
        default_factory=dict,
        description="Accelerator type to its hourly cost policy.",
    )
    runner_cost: ModelLlmRunnerCostPolicy | None = Field(
        default=None, description="CI runner cost policy, when priced."
    )

    @model_validator(mode="after")
    def _keys_are_non_blank(self) -> Self:
        if any(not key.strip() for key in (*self.models, *self.compute_cost)):
            raise ValueError("llm.pricing keys must not be blank")
        return self


__all__ = ["ModelLlmPricingOverlay"]

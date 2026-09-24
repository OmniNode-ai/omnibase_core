# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One model's per-token price in the ``llm.pricing`` overlay (OMN-19391).

Fields ported from infra ``models/pricing/model_pricing_entry.py``, with three
deliberate changes recorded in the W1-core PR:

* prices are per one million tokens and name their currency, as plan section
  3.1 declares the key (infra's manifest priced per thousand, USD implied);
* ``source`` is the closed :class:`EnumLlmPricingSource` (``measured`` or
  ``vendor_list``) and is required, which subsumes infra's separate
  ``confidence`` literal;
* a local model has no pricing entry: its zero cost is the catalog's ``free``
  flag, so there is no local-zero-cost pricing source.
"""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_llm_pricing_source import EnumLlmPricingSource
from omnibase_core.models.config_overlay.model_llm_pricing_evidence import (
    ModelLlmPricingEvidence,
)


class ModelLlmPricingEntry(BaseModel):
    """Input and output price per one million tokens, with provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    input_price_per_1m: float = Field(
        ..., ge=0.0, description="Price per one million input tokens."
    )
    output_price_per_1m: float = Field(
        ..., ge=0.0, description="Price per one million output tokens."
    )
    currency: str = Field(
        ..., pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code."
    )
    effective_date: date = Field(..., description="Date from which this price applies.")
    source: EnumLlmPricingSource = Field(
        ..., description="Whether the price was measured or copied from a list."
    )
    evidence: ModelLlmPricingEvidence | None = Field(
        default=None,
        description="The usage sample behind a measured price. Required when measured.",
    )
    note: str = Field(default="", max_length=512, description="Free-form note.")

    @model_validator(mode="after")
    def _measured_price_carries_evidence(self) -> Self:
        if self.source is EnumLlmPricingSource.MEASURED and self.evidence is None:
            raise ValueError("a measured price must carry its evidence")
        return self


__all__ = ["ModelLlmPricingEntry"]

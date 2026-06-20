# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pinned premium counterfactual for auditable delegation savings (OMN-13355).

When a cheaper tier serves a delegated task the premium (frontier) model never
runs, so the saving is a *modeled counterfactual*, not a measurement of a real
premium call. This DTO pins the counterfactual to an auditable pricing-manifest
value so the saving can be defended:

    savings_usd = counterfactual_cost_usd - actual_cost_usd

``counterfactual_cost_usd`` is a PINNED price-table value (USD per 1,000 tokens,
from the canonical pricing manifest) multiplied by the measured token counts.
There is NO live premium API call — the organisation holds no Anthropic/OpenAI
key and provisions none. The pinned model identifier, per-1k input/output price,
and the manifest ``effective_date`` are all carried so a verifier can recompute
the number from the persisted provenance.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelPremiumCounterfactual(BaseModel):
    """Pinned premium-model counterfactual for one delegated task.

    Every field is provenance: the model whose price was pinned, the two per-1k
    token prices read from the pricing manifest, the manifest ``as_of``
    (effective_date) the price was pinned to, the measured token counts, and the
    derived counterfactual cost. ``counterfactual_cost_usd`` always equals
    ``price_in_per_1k * tokens_in/1000 + price_out_per_1k * tokens_out/1000`` and
    is recomputable from the other fields. No field is defaulted to a placeholder
    — a counterfactual either carries its full pinned provenance or is ``None``
    on the carrying model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    model: str = Field(
        ...,
        min_length=1,
        description=(
            "Premium model identifier whose price was pinned for the "
            "counterfactual (e.g. 'claude-opus-4-6')."
        ),
    )
    price_in_per_1k: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Pinned input-token price in USD per 1,000 tokens.",
    )
    price_out_per_1k: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Pinned output-token price in USD per 1,000 tokens.",
    )
    as_of: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description=(
            "ISO-8601 date (YYYY-MM-DD) the pinned price was effective, carried "
            "verbatim from the pricing manifest entry's effective_date."
        ),
    )
    tokens_in: int = Field(
        ...,
        ge=0,
        description="Measured input (prompt) tokens used to compute the counterfactual.",
    )
    tokens_out: int = Field(
        ...,
        ge=0,
        description="Measured output (completion) tokens used to compute the counterfactual.",
    )
    counterfactual_cost_usd: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description=(
            "Pinned counterfactual cost = price_in_per_1k * tokens_in/1000 + "
            "price_out_per_1k * tokens_out/1000. Recomputable from the other fields."
        ),
    )
    pricing_source: str = Field(
        default="pricing_manifest",
        min_length=1,
        description=(
            "Provenance of the pinned price (e.g. 'pricing_manifest' for the "
            "canonical manifest, 'calibration' for a measured real-premium run)."
        ),
    )
    measured: bool = Field(
        default=False,
        description=(
            "True only when tokens_in/tokens_out were measured from a real premium "
            "run (the OMN-13355 calibration hook); False for the pinned-price "
            "counterfactual computed from the delegated model's own token counts."
        ),
    )

    @model_validator(mode="after")
    def _validate_cost_recomputable(self) -> ModelPremiumCounterfactual:
        """Reject rows whose stored cost does not match the pinned price * tokens.

        Guards the audit invariant: a verifier recomputing the cost from the
        pinned prices and measured tokens must reproduce ``counterfactual_cost_usd``
        exactly. A tiny tolerance absorbs Decimal rounding at the recorded scale.
        """
        recomputed = (
            self.price_in_per_1k * Decimal(self.tokens_in)
            + self.price_out_per_1k * Decimal(self.tokens_out)
        ) / Decimal("1000")
        if abs(recomputed - self.counterfactual_cost_usd) > Decimal("0.000001"):
            raise ValueError(
                "counterfactual_cost_usd must equal "
                "price_in_per_1k * tokens_in/1000 + price_out_per_1k * tokens_out/1000 "
                f"(recomputed={recomputed}, stored={self.counterfactual_cost_usd})"
            )
        return self


__all__: list[str] = ["ModelPremiumCounterfactual"]

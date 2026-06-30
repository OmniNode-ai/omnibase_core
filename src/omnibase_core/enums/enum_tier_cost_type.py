# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed cost-measurement regime for a delegation routing tier (OMN-13234)."""

from __future__ import annotations

from enum import StrEnum


class EnumTierCostType(StrEnum):
    """How a routing tier's actual dollar cost is measured (OMN-13234).

    The flat ``cost_per_1k_tokens`` field models every tier as one per-token
    rate, which cannot express a locally-served tier (zero API cost) or a tier
    with a monthly spend cap and overage rate. This enum names the three
    measurement regimes the delegation ladder actually runs:

    - ``FREE_LOCAL`` — served on owned hardware (local GPU / Mac). No marginal
      API cost; the dollar figure, when needed, comes from the pricing
      manifest's GPU ``compute_cost`` (electricity + amortization), not a
      per-1k token rate. Token-rate cost is always 0.
    - ``METERED`` — billed per token at a fixed ``rate_per_1k_usd`` with no cap
      (e.g. a direct provider key). cost = rate * tokens / 1000.
    - ``BUDGETED`` — billed per token but covered by a monthly spend cap
      (``monthly_cap_usd``). Tokens served while headroom remains cost 0 cash
      (the cap is already paid); tokens served past the cap are billed at
      ``overage_rate_per_1k_usd``.
    """

    FREE_LOCAL = "free_local"
    METERED = "metered"
    BUDGETED = "budgeted"


__all__: list[str] = ["EnumTierCostType"]

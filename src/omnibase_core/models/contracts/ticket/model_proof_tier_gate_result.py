# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelProofTierGateResult — outcome of evaluating a receipt against its required tier.

Returned by
:func:`omnibase_core.validation.validator_proof_tier_gate.evaluate_proof_tier`.
Records the ticket class, the tier its class required, the tier the receipt's
proof packet actually reached (``None`` when no packet was attached), and the
pass/fail decision with a human-readable reason (OMN-13338).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.enums.ticket.enum_ticket_class import EnumTicketClass


class ModelProofTierGateResult(BaseModel):
    """Outcome of comparing a receipt's proof tier to its ticket-class minimum."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    passed: bool = Field(
        ..., description="True when the receipt meets the required tier."
    )
    ticket_class: EnumTicketClass = Field(
        ..., description="Class of the ticket the receipt proves."
    )
    required_tier: EnumProofTier = Field(
        ..., description="Minimum tier the ticket class requires."
    )
    actual_tier: EnumProofTier | None = Field(
        default=None,
        description="Tier the receipt's proof_packet declared; None when absent.",
    )
    reason: str = Field(
        ..., min_length=1, description="Human-readable explanation of the decision."
    )


__all__ = ["ModelProofTierGateResult"]

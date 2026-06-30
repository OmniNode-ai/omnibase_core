# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Proof-tier gate — reject a receipt below the tier required for its ticket class.

Companion to :mod:`omnibase_core.validation.validator_receipt_gate` (OMN-13338).
A ticket's :class:`EnumTicketClass` declares the minimum
:class:`EnumProofTier` a receipt must reach. This module evaluates a single
receipt's :class:`ModelProofPacket` against that minimum and returns a typed
result the receipt gate folds into its decision.

Policy
------
- ticket class has a required tier (every class does — see ``EnumTicketClass``)
- receipt with no ``proof_packet`` AND a required tier above L0 → REJECT
  (absence of a packet cannot satisfy a non-floor requirement)
- receipt whose packet tier ``satisfies`` the required tier → PASS
- receipt whose packet tier is below the required tier → REJECT

The function is pure (no I/O) so the gate, ``node_dod_verify``, and unit tests
all exercise the identical decision path.
"""

from __future__ import annotations

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.enums.ticket.enum_ticket_class import EnumTicketClass
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_proof_tier_gate_result import (
    ModelProofTierGateResult,
)


def evaluate_proof_tier(
    receipt: ModelDodReceipt,
    ticket_class: EnumTicketClass,
) -> ModelProofTierGateResult:
    """Return whether ``receipt`` meets the minimum proof tier for ``ticket_class``.

    Args:
        receipt: The receipt under test.
        ticket_class: The class of the ticket the receipt proves.

    Returns:
        :class:`ModelProofTierGateResult` with ``passed`` and a reason string.
    """
    required = ticket_class.required_tier

    packet = receipt.proof_packet
    if packet is None:
        # An absent packet only satisfies the floor (L0). Any higher requirement
        # cannot be met without a packet declaring the depth.
        if required is EnumProofTier.L0:
            return ModelProofTierGateResult(
                passed=True,
                ticket_class=ticket_class,
                required_tier=required,
                actual_tier=None,
                reason=(
                    f"ticket class {ticket_class.value} requires tier "
                    f"{required.value} (floor); receipt without a proof_packet "
                    "is accepted at the floor."
                ),
            )
        return ModelProofTierGateResult(
            passed=False,
            ticket_class=ticket_class,
            required_tier=required,
            actual_tier=None,
            reason=(
                f"PROOF TIER GATE FAILED: ticket class {ticket_class.value} "
                f"requires tier {required.value} but the receipt has no "
                "proof_packet. Attach a ModelProofPacket at or above the "
                "required tier."
            ),
        )

    if packet.tier.satisfies(required):
        return ModelProofTierGateResult(
            passed=True,
            ticket_class=ticket_class,
            required_tier=required,
            actual_tier=packet.tier,
            reason=(
                f"proof_packet tier {packet.tier.value} satisfies the "
                f"{required.value} required for ticket class {ticket_class.value}."
            ),
        )

    return ModelProofTierGateResult(
        passed=False,
        ticket_class=ticket_class,
        required_tier=required,
        actual_tier=packet.tier,
        reason=(
            f"PROOF TIER GATE FAILED: ticket class {ticket_class.value} requires "
            f"tier {required.value} but the receipt's proof_packet is only "
            f"{packet.tier.value}. Produce a higher-tier packet with the fields "
            "that tier requires."
        ),
    )


__all__ = ["evaluate_proof_tier"]

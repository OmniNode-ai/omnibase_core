# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumTicketClass — the kind of change a ticket represents, with its minimum proof tier.

The receipt gate compares a receipt's :class:`EnumProofTier` against the
minimum tier required for the ticket's class. A docs-only change need only
prove L0 (PR + CI); a customer-facing change must prove L3 (dashboard +
network + replay). Mapping the class to a *minimum* (not exact) tier keeps the
gate from forcing an over-heavyweight packet on a small change while still
rejecting an under-evidenced one.

Members
-------
DOCS
    Documentation / non-code change. Minimum tier L0.
CODE
    Source change with tests but no runtime/deploy surface. Minimum tier L1.
RUNTIME
    Change that alters deployed runtime behavior. Minimum tier L2.
CUSTOMER
    Change with a customer-visible surface (dashboard / network). Minimum
    tier L3.
"""

from __future__ import annotations

from enum import StrEnum

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier


class EnumTicketClass(StrEnum):
    """Class of change a ticket represents; determines the minimum proof tier."""

    DOCS = "docs"
    CODE = "code"
    RUNTIME = "runtime"
    CUSTOMER = "customer"

    @property
    def required_tier(self) -> EnumProofTier:
        """Return the minimum :class:`EnumProofTier` a receipt for this class must reach."""
        return _CLASS_REQUIRED_TIER[self]


# Single source of truth for class -> minimum required tier. Kept as a
# module-level frozen mapping (not a method body) so the policy is grep-able
# and a static check can assert every class has an entry.
_CLASS_REQUIRED_TIER: dict[EnumTicketClass, EnumProofTier] = {
    EnumTicketClass.DOCS: EnumProofTier.L0,
    EnumTicketClass.CODE: EnumProofTier.L1,
    EnumTicketClass.RUNTIME: EnumProofTier.L2,
    EnumTicketClass.CUSTOMER: EnumProofTier.L3,
}


__all__ = ["EnumTicketClass"]

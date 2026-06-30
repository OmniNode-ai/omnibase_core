# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumProofTier — graded evidence depth (L0-L3) for a DoD proof packet.

A receipt without a graded tier makes a weak proof indistinguishable from a
strong one. ``EnumProofTier`` ranks evidence depth so the receipt gate can
reject a receipt whose tier is below the tier required for its ticket class
(see :class:`omnibase_core.enums.ticket.enum_ticket_class.EnumTicketClass`).

Tiers are cumulative — each higher tier requires every field of the tier(s)
below it, plus its own additional fields. The ordering is what lets the gate
compare two tiers with ``>=``; do not reorder members without updating
``rank``.

Members
-------
L0
    Docs class. Required fields: pr_url, ci_status. Proves a PR exists and CI
    reached a terminal state — the floor for any change.
L1
    Code class. L0 + merged_pr_url, test_evidence. Proves the change merged
    and a test exercised the changed behavior.
L2
    Runtime class. L1 + runtime_sha, image_digest, correlation_id,
    terminal_event, projection_ref. Proves the change is live and a workflow
    transited the bus to a terminal state with a materialized projection.
L3
    Customer class. L2 + dashboard_ref, network_evidence, replay_class.
    Proves a customer-visible surface rendered the change and the run is
    replayable.
"""

from __future__ import annotations

from enum import StrEnum


class EnumProofTier(StrEnum):
    """Graded evidence-depth tier for a DoD proof packet (L0 lowest, L3 highest)."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"

    @property
    def rank(self) -> int:
        """Return the numeric rank (0-3) so tiers can be compared by depth.

        ``EnumProofTier.L2.rank >= EnumProofTier.L1.rank`` is the canonical
        "is this packet at least the required tier" comparison. Implemented as
        an int extracted from the member name rather than a hand-maintained
        map so a new tier (e.g. ``L4``) ranks correctly without a second edit.
        """
        return int(self.value[1:])

    def satisfies(self, required: EnumProofTier) -> bool:
        """Return True when this tier is at or above ``required``."""
        return self.rank >= required.rank


__all__ = ["EnumProofTier"]

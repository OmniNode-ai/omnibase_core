# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumProofTier ordering and EnumTicketClass mapping (OMN-13338)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.enums.ticket.enum_ticket_class import EnumTicketClass


@pytest.mark.unit
class TestProofTierRanking:
    def test_ranks_are_monotonic(self) -> None:
        assert (
            EnumProofTier.L0.rank
            < EnumProofTier.L1.rank
            < EnumProofTier.L2.rank
            < EnumProofTier.L3.rank
        )

    def test_satisfies_at_or_above(self) -> None:
        assert EnumProofTier.L2.satisfies(EnumProofTier.L1)
        assert EnumProofTier.L2.satisfies(EnumProofTier.L2)

    def test_does_not_satisfy_below(self) -> None:
        assert not EnumProofTier.L1.satisfies(EnumProofTier.L2)
        assert not EnumProofTier.L0.satisfies(EnumProofTier.L3)


@pytest.mark.unit
class TestTicketClassRequiredTier:
    @pytest.mark.parametrize(
        ("ticket_class", "expected"),
        [
            (EnumTicketClass.DOCS, EnumProofTier.L0),
            (EnumTicketClass.CODE, EnumProofTier.L1),
            (EnumTicketClass.RUNTIME, EnumProofTier.L2),
            (EnumTicketClass.CUSTOMER, EnumProofTier.L3),
        ],
    )
    def test_required_tier_mapping(
        self, ticket_class: EnumTicketClass, expected: EnumProofTier
    ) -> None:
        assert ticket_class.required_tier is expected

    def test_every_class_has_a_required_tier(self) -> None:
        for ticket_class in EnumTicketClass:
            # Must not raise KeyError — every member is mapped.
            assert isinstance(ticket_class.required_tier, EnumProofTier)

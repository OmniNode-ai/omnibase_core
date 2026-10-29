# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The substance floor and one check's derived tier (OMN-14409, ported for OMN-17427).

Split out of ``handler_contract_substance_floor`` so each module holds one class;
that module re-exports both names.
"""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier

__all__ = ["SUBSTANCE_FLOOR", "CheckFinding"]

# The floor. A contract needs at least one check at or above this tier.
SUBSTANCE_FLOOR = EnumProofTier.L1


@dataclass
class CheckFinding:
    """One dod_evidence check and the tier it derives to."""

    #: the dod_evidence item's ``id`` (``item_id`` in the OCC original)
    dod_item: str
    check_type: str
    check_value: str
    tier: EnumProofTier

    @property
    def is_substantive(self) -> bool:
        return self.tier.satisfies(SUBSTANCE_FLOOR)

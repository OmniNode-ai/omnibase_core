# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Verification tier enum for contract.verify.replay.

Defines the two-tier verification model: tier1_static (structural/schema
checks) and tier2_simulated (virtual clock replay). Only tier1_static is
implemented in the MVP (OMN-2759).

.. versionadded:: 0.20.0
"""

from enum import Enum

__all__ = ["EnumVerifyTier"]


class EnumVerifyTier(str, Enum):
    """Verification tier for contract.verify.replay.

    Attributes:
        TIER1_STATIC: Schema validation, capability linting, fixture presence,
            overlay merge correctness, and determinism class checks. Does not
            require executing any replay sessions.
        TIER2_SIMULATED: Full virtual-clock replay with fixture adapters,
            checkpoint hashing, and invariant evaluation. Deferred to a future
            ticket.
    """

    TIER1_STATIC = "tier1_static"
    TIER2_SIMULATED = "tier2_simulated"

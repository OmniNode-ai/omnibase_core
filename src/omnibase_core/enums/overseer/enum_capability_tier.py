# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum
from functools import total_ordering


@total_ordering
class EnumCapabilityTier(StrEnum):
    """Capability tier for overseer routing decisions.

    Ordered C0 (lowest) through C4 (highest). Supports comparison operators
    via @total_ordering for tier-based routing logic.
    """

    C0 = "C0"
    """Tier 0 — minimal capability."""

    C1 = "C1"
    """Tier 1 — basic capability."""

    C2 = "C2"
    """Tier 2 — standard capability."""

    C3 = "C3"
    """Tier 3 — advanced capability."""

    C4 = "C4"
    """Tier 4 — maximum capability."""

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EnumCapabilityTier):
            return NotImplemented
        members = list(EnumCapabilityTier)
        return members.index(self) < members.index(other)


__all__: list[str] = ["EnumCapabilityTier"]

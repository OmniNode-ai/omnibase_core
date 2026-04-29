# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum
from functools import total_ordering


@total_ordering
class EnumContextBundleLevel(StrEnum):
    """Context bundle verbosity level for overseer context injection.

    Ordered L0 (minimal) through L4 (maximum). Controls how much context
    is bundled for agent dispatch.
    """

    L0 = "L0"
    """Level 0 — minimal context (ticket ID only)."""

    L1 = "L1"
    """Level 1 — basic context (ticket + summary)."""

    L2 = "L2"
    """Level 2 — standard context (ticket + summary + entrypoints)."""

    L3 = "L3"
    """Level 3 — rich context (standard + related decisions + history)."""

    L4 = "L4"
    """Level 4 — maximum context (everything available)."""

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EnumContextBundleLevel):
            return NotImplemented
        members = list(EnumContextBundleLevel)
        return members.index(self) < members.index(other)


__all__: list[str] = ["EnumContextBundleLevel"]

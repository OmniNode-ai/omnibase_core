# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tie-breaker strategy enumeration for the Decision Provenance system.

Defines the canonical set of strategies used when multiple decision candidates
score equally and a deterministic selection rule is needed.

Part of the Decision Provenance system (OMN-2350).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTieBreakerStrategy(StrValueHelper, str, Enum):
    """Canonical tie-breaker strategies for provenance decision records.

    When multiple candidates share the same score, a tie-breaker strategy
    is applied to produce a deterministic selection. This enum classifies
    the strategy used so that provenance records are reproducible and auditable.

    Values:
        RANDOM: Randomly select among tied candidates (non-deterministic).
        ALPHABETICAL: Select the lexicographically earliest candidate identifier.
        COST_ASCENDING: Select the candidate with the lowest estimated cost.

    Example:
        >>> strategy = EnumTieBreakerStrategy.ALPHABETICAL
        >>> str(strategy)
        'alphabetical'

        >>> # Use with Pydantic (string coercion works)
        >>> from pydantic import BaseModel
        >>> class Record(BaseModel):
        ...     tie_breaker: EnumTieBreakerStrategy | None = None
        >>> r = Record(tie_breaker="random")
        >>> r.tie_breaker == EnumTieBreakerStrategy.RANDOM
        True
    """

    RANDOM = "random"
    """Randomly select among tied candidates (non-deterministic run-to-run)."""

    ALPHABETICAL = "alphabetical"
    """Select the lexicographically earliest candidate identifier."""

    COST_ASCENDING = "cost_ascending"
    """Select the candidate with the lowest estimated cost."""

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string value is a valid enum member.

        Args:
            value: The string value to check.

        Returns:
            True if the value is a valid enum member, False otherwise.

        Example:
            >>> EnumTieBreakerStrategy.is_valid("random")
            True
            >>> EnumTieBreakerStrategy.is_valid("unknown")
            False
        """
        return value in cls._value2member_map_


__all__ = ["EnumTieBreakerStrategy"]

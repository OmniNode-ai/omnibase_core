# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Type Category Enumeration.

Classifies handlers by computational behavior.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumHandlerTypeCategory(str, Enum):
    """
    Enumeration of handler type categories.

    SINGLE SOURCE OF TRUTH for handler behavioral classification.
    Classifies handlers by computational behavior (pure/impure, deterministic/non-deterministic).

    Note: ADAPTER is NOT a category—it's a policy tag (see ModelHandlerDescriptor).

    Categories:
        COMPUTE: Pure, deterministic computation
        EFFECT: Side-effecting I/O operations
        NONDETERMINISTIC_COMPUTE: Pure but non-deterministic

    Example:
        >>> from omnibase_core.enums import EnumHandlerTypeCategory
        >>> cat = EnumHandlerTypeCategory.COMPUTE
        >>> str(cat)
        'compute'
    """

    COMPUTE = "compute"
    """Pure, deterministic handler. Same input always produces same output."""

    EFFECT = "effect"
    """Side-effecting I/O handler. Interacts with external systems (files, network, database)."""

    NONDETERMINISTIC_COMPUTE = "nondeterministic_compute"
    """Pure but non-deterministic handler. No side effects but output varies (e.g., random, time-based)."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensure exhaustive handling in match statements."""
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerTypeCategory"]

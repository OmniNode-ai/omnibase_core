# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Enumeration for invariant violation severity levels."""

from enum import Enum

from omnibase_core.utils.util_str_enum_base import StrValueHelper


class EnumInvariantSeverity(StrValueHelper, str, Enum):
    """Severity levels for invariant violations.

    Ordered from least to most severe for threshold comparisons.
    Use numeric comparison via severity_order property.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def severity_order(self) -> int:
        """Numeric order for severity comparisons. Higher = more severe."""
        return _SEVERITY_ORDER[self]

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, EnumInvariantSeverity):
            return NotImplemented
        return self.severity_order >= other.severity_order

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, EnumInvariantSeverity):
            return NotImplemented
        return self.severity_order > other.severity_order

    def __le__(self, other: object) -> bool:
        if not isinstance(other, EnumInvariantSeverity):
            return NotImplemented
        return self.severity_order <= other.severity_order

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EnumInvariantSeverity):
            return NotImplemented
        return self.severity_order < other.severity_order


# Module-level severity ordering map (cached, not recreated on each property access)
_SEVERITY_ORDER: dict["EnumInvariantSeverity", int] = {
    EnumInvariantSeverity.INFO: 0,
    EnumInvariantSeverity.WARNING: 1,
    EnumInvariantSeverity.CRITICAL: 2,
}

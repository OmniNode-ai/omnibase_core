# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Invariant Status Enum.

Status values for invariant checks in daily close reports.
"""

from enum import Enum, unique


@unique
class EnumInvariantStatus(str, Enum):
    """Status values for ONEX invariant checks.

    Invariant status values:
    - pass: Invariant is satisfied
    - fail: Invariant is violated
    - unknown: Invariant status cannot be determined (requires follow-up)
    """

    PASS = "pass"
    """Invariant is satisfied."""

    FAIL = "fail"
    """Invariant is violated."""

    UNKNOWN = "unknown"
    """Invariant status cannot be determined (requires follow-up)."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

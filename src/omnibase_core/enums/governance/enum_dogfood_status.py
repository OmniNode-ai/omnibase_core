# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dogfood Status Enum.

Status values for model dogfood scorecard dimensions and regression detection.
"""

from enum import Enum, unique


@unique
class EnumDogfoodStatus(str, Enum):
    """Status values for dogfood scorecard checks.

    Status values:
    - pass: Check is healthy
    - warn: Degraded but not broken
    - fail: Check is broken or missing
    - unknown: Status cannot be determined
    """

    PASS = "pass"
    """Check is healthy."""

    WARN = "warn"
    """Degraded but not broken."""

    FAIL = "fail"
    """Check is broken or missing."""

    UNKNOWN = "unknown"
    """Status cannot be determined."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


@unique
class EnumRegressionSeverity(str, Enum):
    """Severity levels for detected regressions.

    Severity values:
    - critical: Immediate action required (e.g., healthy chain drops to 0 rows)
    - warn: Degraded but not immediately blocking
    - none: No regression detected
    """

    CRITICAL = "critical"
    """Immediate action required."""

    WARN = "warn"
    """Degraded but not immediately blocking."""

    NONE = "none"
    """No regression detected."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

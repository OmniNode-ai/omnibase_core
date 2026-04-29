# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Finding Severity Enum.

Severity levels for aggregated morning investigation findings.
"""

from enum import Enum, unique


@unique
class EnumFindingSeverity(str, Enum):
    """Severity levels for begin-day investigation findings.

    Used by ModelDayOpen to classify findings from parallel probes:
    - CRITICAL: Immediate action required, blocks development
    - HIGH: Should be addressed today
    - MEDIUM: Should be addressed soon
    - LOW: Minor issue, address when convenient
    - INFO: Informational, no action required
    """

    CRITICAL = "critical"
    """Immediate action required, blocks development."""

    HIGH = "high"
    """Should be addressed today."""

    MEDIUM = "medium"
    """Should be addressed soon."""

    LOW = "low"
    """Minor issue, address when convenient."""

    INFO = "info"
    """Informational, no action required."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

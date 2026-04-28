# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumRiskLevel(StrEnum):
    """Risk level for overseer routing policy decisions."""

    LOW = "low"
    """Low risk — minimal validation required."""

    MEDIUM = "medium"
    """Medium risk — standard validation applied."""

    HIGH = "high"
    """High risk — elevated scrutiny and human review gate."""

    CRITICAL = "critical"
    """Critical risk — requires explicit authorization before dispatch."""


__all__: list[str] = ["EnumRiskLevel"]

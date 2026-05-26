# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Risk level enum for routing policy decisions."""

from enum import StrEnum


class EnumRiskLevel(StrEnum):
    """Risk level of the routing decision."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


__all__: list[str] = ["EnumRiskLevel"]

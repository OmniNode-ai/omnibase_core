# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnumThroughputLevel: Enumeration of throughput levels.

This enum defines the throughput levels for performance profiles.
"""

from enum import Enum, unique


@unique
class EnumThroughputLevel(Enum):
    """Throughput levels for performance profiles."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

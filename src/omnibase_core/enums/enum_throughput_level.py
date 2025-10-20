"""
EnumThroughputLevel: Enumeration of throughput levels.

This enum defines the throughput levels for performance profiles.
"""

from enum import Enum


class EnumThroughputLevel(Enum):
    """Throughput levels for performance profiles."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

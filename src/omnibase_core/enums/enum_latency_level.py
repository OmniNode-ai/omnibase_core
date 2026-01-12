"""
EnumLatencyLevel: Enumeration of latency levels.

This enum defines the latency levels for performance profiles.
"""

from enum import Enum, unique


@unique
class EnumLatencyLevel(Enum):
    """Latency levels for performance profiles."""

    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

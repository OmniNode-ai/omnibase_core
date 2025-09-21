"""
Fallback strategy type enum.

This module provides the FallbackStrategyType enum for defining
core fallback strategy types in the ONEX Configuration-Driven Registry System.
"""

from enum import Enum


class FallbackStrategyType(str, Enum):
    """Core fallback strategy types."""

    BOOTSTRAP = "bootstrap"
    EMERGENCY = "emergency"
    LOCAL = "local"
    DEGRADED = "degraded"
    FAIL_FAST = "fail_fast"

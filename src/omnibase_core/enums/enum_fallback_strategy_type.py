from __future__ import annotations

"""
Fallback strategy type enum.

This module provides the EnumFallbackStrategyType enum for defining
core fallback strategy types in the ONEX Configuration-Driven Registry System.
"""


from enum import Enum, unique


@unique
class EnumFallbackStrategyType(str, Enum):
    """Core fallback strategy types."""

    BOOTSTRAP = "bootstrap"
    EMERGENCY = "emergency"
    LOCAL = "local"
    DEGRADED = "degraded"
    FAIL_FAST = "fail_fast"


__all__ = ["EnumFallbackStrategyType"]

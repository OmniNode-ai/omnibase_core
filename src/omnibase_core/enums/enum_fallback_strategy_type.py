"""
Fallback strategy type enum.

This module provides the EnumFallbackStrategyType enum for defining
core fallback strategy types in the ONEX Configuration-Driven Registry System.
"""

from __future__ import annotations

from enum import Enum


class EnumFallbackStrategyType(str, Enum):
    """Core fallback strategy types."""

    BOOTSTRAP = "bootstrap"
    EMERGENCY = "emergency"
    LOCAL = "local"
    DEGRADED = "degraded"
    FAIL_FAST = "fail_fast"

"""
Fallback strategy type enum.

This module provides the EnumFallbackStrategyType enum for defining
core fallback strategy types in the ONEX Configuration-Driven Registry System.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFallbackStrategyType(StrValueHelper, str, Enum):
    """Core fallback strategy types."""

    BOOTSTRAP = "bootstrap"
    EMERGENCY = "emergency"
    LOCAL = "local"
    DEGRADED = "degraded"
    FAIL_FAST = "fail_fast"


__all__ = ["EnumFallbackStrategyType"]

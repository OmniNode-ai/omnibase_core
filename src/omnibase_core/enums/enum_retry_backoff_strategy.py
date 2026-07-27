# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Retry Backoff Strategy Enumeration.

Defines the available retry backoff strategies for retry policies.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumRetryBackoffStrategy(UtilStrValueHelper, str, Enum):
    """Retry backoff strategy enumeration."""

    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linearly increasing delay
    EXPONENTIAL = "exponential"  # Exponentially increasing delay
    RANDOM = "random"  # Random delay within range
    FIBONACCI = "fibonacci"  # Fibonacci sequence delays


# Export for use
__all__ = ["EnumRetryBackoffStrategy"]

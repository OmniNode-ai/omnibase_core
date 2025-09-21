"""
Retry Backoff Strategy Enumeration.

Defines the available retry backoff strategies for retry policies.
"""

from __future__ import annotations

from enum import Enum


class RetryBackoffStrategy(Enum):
    """Retry backoff strategy enumeration."""

    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linearly increasing delay
    EXPONENTIAL = "exponential"  # Exponentially increasing delay
    RANDOM = "random"  # Random delay within range
    FIBONACCI = "fibonacci"  # Fibonacci sequence delays


# Export for use
__all__ = ["RetryBackoffStrategy"]

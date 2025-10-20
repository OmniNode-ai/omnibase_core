from __future__ import annotations

"""
Retry Backoff Strategy Enumeration.

Defines the available retry backoff strategies for retry policies.
"""


from enum import Enum, unique


@unique
class EnumRetryBackoffStrategy(str, Enum):
    """Retry backoff strategy enumeration."""

    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linearly increasing delay
    EXPONENTIAL = "exponential"  # Exponentially increasing delay
    RANDOM = "random"  # Random delay within range
    FIBONACCI = "fibonacci"  # Fibonacci sequence delays

    def __str__(self) -> str:
        return self.value  # Return string value of the strategy


# Export for use
__all__ = ["EnumRetryBackoffStrategy"]

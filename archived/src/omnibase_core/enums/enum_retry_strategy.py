"""
Retry strategy enum for error recovery operations.

Defines different retry approaches based on error type and context.
"""

from enum import Enum


class EnumRetryStrategy(str, Enum):
    """Retry strategies for error recovery."""

    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL_INTERVENTION = "manual_intervention"

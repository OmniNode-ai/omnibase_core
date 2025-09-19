"""
Backoff strategy enum for error handling configurations.
"""

from enum import Enum


class EnumBackoffStrategy(str, Enum):
    """Supported backoff strategies for error handling and retries."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    POLYNOMIAL = "polynomial"
    FIBONACCI = "fibonacci"
    JITTERED = "jittered"
    NONE = "none"

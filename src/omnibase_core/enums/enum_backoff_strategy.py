"""
Backoff Strategy Enumeration.

Retry backoff strategies for infrastructure resilience in ONEX systems.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumBackoffStrategy(StrValueHelper, str, Enum):
    """Enumeration for retry backoff strategies used in infrastructure components."""

    # Backoff strategies for retry logic
    EXPONENTIAL = "EXPONENTIAL"  # Exponential backoff (2^attempt * base_delay)
    LINEAR = "LINEAR"  # Linear backoff (attempt * base_delay)
    FIXED = "FIXED"  # Fixed delay between retries


__all__ = ["EnumBackoffStrategy"]

"""Circuit breaker state enumeration for failure handling."""

from enum import Enum


class EnumCircuitBreakerState(Enum):
    """Circuit breaker states for failure handling."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered

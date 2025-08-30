"""Circuit breaker states for intelligent context routing protection mechanisms."""

from enum import Enum


class EnumCircuitBreakerState(str, Enum):
    """States of circuit breakers in the safety system."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

"""
Effect-related enumerations for NodeEffect operations.

Defines types of side effects, transaction states, and circuit breaker states
for managing external interactions and resilience patterns.

Author: ONEX Framework Team
"""

from enum import Enum

__all__ = [
    "EnumEffectType",
    "EnumTransactionState",
    "EnumCircuitBreakerState",
]


class EnumEffectType(Enum):
    """Types of side effects that can be managed."""

    FILE_OPERATION = "file_operation"
    DATABASE_OPERATION = "database_operation"
    API_CALL = "api_call"
    EVENT_EMISSION = "event_emission"
    DIRECTORY_OPERATION = "directory_operation"
    TICKET_STORAGE = "ticket_storage"
    METRICS_COLLECTION = "metrics_collection"


class EnumTransactionState(Enum):
    """Transaction state tracking."""

    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class EnumCircuitBreakerState(Enum):
    """Circuit breaker states for failure handling."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered

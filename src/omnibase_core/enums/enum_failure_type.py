"""
Failure Type Enum.

Provides type-safe classification of failure types for systematic
analysis of failure patterns across memory snapshots.
"""

from enum import Enum, unique


@unique
class EnumFailureType(str, Enum):
    """Failure types for memory snapshot classification.

    Each failure in a memory snapshot is tagged with its type,
    enabling systematic analysis of failure patterns. This enum
    supports the omnimemory system for tracking and categorizing
    failures across agent executions.

    Example:
        >>> failure_type = EnumFailureType.TIMEOUT
        >>> str(failure_type)
        'timeout'

        >>> # Use with Pydantic (string coercion works)
        >>> from pydantic import BaseModel
        >>> class FailureRecord(BaseModel):
        ...     failure_type: EnumFailureType
        >>> record = FailureRecord(failure_type="validation_error")
        >>> record.failure_type == EnumFailureType.VALIDATION_ERROR
        True
    """

    INVARIANT_VIOLATION = "invariant_violation"
    """A required invariant or constraint was violated."""

    TIMEOUT = "timeout"
    """Operation exceeded its time limit."""

    MODEL_ERROR = "model_error"
    """Error from the AI model (generation failure, context overflow, etc.)."""

    COST_EXCEEDED = "cost_exceeded"
    """Operation exceeded its allocated cost budget."""

    VALIDATION_ERROR = "validation_error"
    """Input or output validation failed."""

    EXTERNAL_SERVICE = "external_service"
    """External service or API failure (network, unavailable, etc.)."""

    RATE_LIMIT = "rate_limit"
    """Rate limit exceeded for an API or service."""

    UNKNOWN = "unknown"
    """Unclassified failure (escape hatch for unexpected failure modes)."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


__all__ = ["EnumFailureType"]

"""
Failure Type Enum.

Provides type-safe classification of failure types for systematic
analysis of failure patterns across memory snapshots.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFailureType(StrValueHelper, str, Enum):
    """Failure type classification for omnimemory snapshots.

    Classifies failures recorded in memory snapshots to enable systematic
    analysis of failure patterns across agent executions. Each failure event
    is tagged with its type to support retry logic, alerting, and post-mortem
    analysis in the omnimemory system.

    See Also:
        - docs/omnimemory/memory_snapshots.md: Memory snapshot architecture
        - EnumDecisionType: Classification of decisions (e.g., retry decisions)
        - EnumSubjectType: Classification of memory ownership

    Values:
        INVARIANT_VIOLATION: A required invariant or constraint was violated
        TIMEOUT: Operation exceeded its time limit
        MODEL_ERROR: Error from the AI model (generation failure, context overflow)
        COST_EXCEEDED: Operation exceeded its allocated cost budget
        VALIDATION_ERROR: Input or output validation failed
        EXTERNAL_SERVICE: External service or API failure (network, unavailable)
        RATE_LIMIT: Rate limit exceeded for an API or service
        UNKNOWN: Unclassified failure (escape hatch for unexpected failure modes)

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

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string value is a valid enum member.

        Args:
            value: The string value to check.

        Returns:
            True if the value is a valid enum member, False otherwise.

        Example:
            >>> EnumFailureType.is_valid("timeout")
            True
            >>> EnumFailureType.is_valid("invalid_type")
            False
        """
        return value in cls._value2member_map_

    def is_retryable(self) -> bool:
        """Check if this failure type is typically retryable.

        Returns:
            True if this failure type may be resolved by retrying.

        Example:
            >>> EnumFailureType.TIMEOUT.is_retryable()
            True
            >>> EnumFailureType.INVARIANT_VIOLATION.is_retryable()
            False
        """
        return self in {
            EnumFailureType.EXTERNAL_SERVICE,
            EnumFailureType.MODEL_ERROR,
            EnumFailureType.RATE_LIMIT,
            EnumFailureType.TIMEOUT,
        }

    def is_resource_related(self) -> bool:
        """Check if this failure type is related to resource constraints.

        Returns:
            True if this failure is caused by resource limits or constraints.

        Example:
            >>> EnumFailureType.COST_EXCEEDED.is_resource_related()
            True
            >>> EnumFailureType.VALIDATION_ERROR.is_resource_related()
            False
        """
        return self in {
            EnumFailureType.COST_EXCEEDED,
            EnumFailureType.RATE_LIMIT,
            EnumFailureType.TIMEOUT,
        }


__all__ = ["EnumFailureType"]

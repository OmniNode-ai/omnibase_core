"""
Failure type enum for failure classification.

Provides type-safe classification of failure types for systematic
analysis of failure patterns across memory snapshots.
"""

from enum import Enum


class EnumFailureType(str, Enum):
    """Failure types for classification.

    Each failure in a memory snapshot is tagged with its type,
    enabling systematic analysis of failure patterns.

    Attributes:
        INVARIANT_VIOLATION: A required invariant or constraint was violated
        TIMEOUT: Operation exceeded its time limit
        MODEL_ERROR: Error from the AI model (generation failure, etc.)
        COST_EXCEEDED: Operation exceeded cost budget
        VALIDATION_ERROR: Input or output validation failed
        EXTERNAL_SERVICE: External service or API failure
        RATE_LIMIT: Rate limit exceeded
        UNKNOWN: Unclassified failure (escape hatch)
    """

    INVARIANT_VIOLATION = "invariant_violation"
    TIMEOUT = "timeout"
    MODEL_ERROR = "model_error"
    COST_EXCEEDED = "cost_exceeded"
    VALIDATION_ERROR = "validation_error"
    EXTERNAL_SERVICE = "external_service"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"

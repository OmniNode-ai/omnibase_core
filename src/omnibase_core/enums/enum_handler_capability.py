"""
Handler Capability Enumeration.

Unified handler capabilities that span all node types.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumHandlerCapability(str, Enum):
    """
    Enumeration of unified handler capabilities.

    SINGLE SOURCE OF TRUTH for handler-level capabilities.
    These capabilities apply across all node types (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR).

    Note: For node-specific capabilities, see:
    - EnumComputeCapability
    - EnumEffectCapability
    - EnumReducerCapability
    - EnumOrchestratorCapability

    Capabilities:
        TRANSFORM: Data transformation capability
        VALIDATE: Input/output validation capability
        CACHE: Result caching capability
        RETRY: Automatic retry capability
        BATCH: Batch processing capability
        STREAM: Streaming data capability
        ASYNC: Asynchronous execution capability
        IDEMPOTENT: Idempotent operation capability

    Example:
        >>> from omnibase_core.enums import EnumHandlerCapability
        >>> cap = EnumHandlerCapability.CACHE
        >>> str(cap)
        'cache'
    """

    TRANSFORM = "transform"
    """Can transform data between formats."""

    VALIDATE = "validate"
    """Can validate input/output data."""

    CACHE = "cache"
    """Supports caching of results for performance."""

    RETRY = "retry"
    """Supports automatic retry on transient failures."""

    BATCH = "batch"
    """Supports batch processing of multiple items."""

    STREAM = "stream"
    """Supports streaming data processing."""

    ASYNC = "async"
    """Supports asynchronous execution."""

    IDEMPOTENT = "idempotent"
    """Operation is idempotent (can safely retry without side effects)."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling in match statements."""
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerCapability"]

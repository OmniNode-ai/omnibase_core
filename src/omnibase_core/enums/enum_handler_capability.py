"""Handler capability enumeration for cross-cutting features like caching, retry, and batching."""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerCapability(StrValueHelper, str, Enum):
    """
    Unified handler capabilities for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.

    Capabilities: TRANSFORM, VALIDATE, CACHE, RETRY, BATCH, STREAM, ASYNC, IDEMPOTENT.

    Note: EFFECT handlers with CACHE or RETRY should also declare IDEMPOTENT.
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

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling in match statements.

        Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerCapability"]

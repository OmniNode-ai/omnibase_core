"""Handler type category enumeration for behavioral classification."""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerTypeCategory(StrValueHelper, str, Enum):
    """Behavioral classification of handlers (pure/impure, deterministic/non-deterministic).

    Categories: COMPUTE (pure, deterministic), EFFECT (impure), NONDETERMINISTIC_COMPUTE.
    """

    COMPUTE = "compute"
    """Pure, deterministic handler. Same input always produces same output."""

    EFFECT = "effect"
    """Side-effecting I/O handler. Interacts with external systems (files, network, database)."""

    NONDETERMINISTIC_COMPUTE = "nondeterministic_compute"
    """Pure but non-deterministic handler. No side effects but output varies (e.g., random, time-based)."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensure exhaustive handling in match statements.

        Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerTypeCategory"]

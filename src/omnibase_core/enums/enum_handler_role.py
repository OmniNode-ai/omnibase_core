"""Handler role enumeration for architectural classification in ONEX."""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerRole(StrValueHelper, str, Enum):
    """Architectural role classification of handlers.

    Roles: INFRA_HANDLER (protocol/transport), NODE_HANDLER (event/business logic),
    PROJECTION_HANDLER (read model), COMPUTE_HANDLER (pure computation).
    """

    INFRA_HANDLER = "infra_handler"
    """Protocol/transport handler. Manages communication infrastructure (HTTP, Kafka, etc.)."""

    NODE_HANDLER = "node_handler"
    """Event processing handler. Implements business logic via event-driven patterns."""

    PROJECTION_HANDLER = "projection_handler"
    """Projection read/write handler. Manages read models and materialized views."""

    COMPUTE_HANDLER = "compute_handler"
    """Pure computation handler. Performs stateless transformations without side effects."""

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


__all__ = ["EnumHandlerRole"]

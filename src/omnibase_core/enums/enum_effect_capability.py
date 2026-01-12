"""
Effect Capability Enumeration.

Defines the available capabilities for EFFECT nodes in the ONEX four-node architecture.
EFFECT nodes handle external interactions (I/O) including API calls, database operations,
file system access, and message queues.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEffectCapability(StrValueHelper, str, Enum):
    """Effect node capabilities: HTTP, DB, KAFKA, FILESYSTEM for external I/O."""

    HTTP = "http"
    """HTTP/REST API interactions."""

    DB = "db"
    """Database operations (SQL, NoSQL)."""

    KAFKA = "kafka"
    """Apache Kafka message queue operations."""

    FILESYSTEM = "filesystem"
    """File system read/write operations."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all capability values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match capability:
                case EnumEffectCapability.HTTP:
                    handle_http()
                case EnumEffectCapability.DB:
                    handle_db()
                case EnumEffectCapability.KAFKA:
                    handle_kafka()
                case EnumEffectCapability.FILESYSTEM:
                    handle_filesystem()
                case _ as unreachable:
                    EnumEffectCapability.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumEffectCapability"]

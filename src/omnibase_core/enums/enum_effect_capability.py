"""
Effect Capability Enumeration.

Defines the available capabilities for EFFECT nodes in the ONEX four-node architecture.
EFFECT nodes handle external interactions (I/O) including API calls, database operations,
file system access, and message queues.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumEffectCapability(str, Enum):
    """
    Enumeration of supported effect node capabilities.

    SINGLE SOURCE OF TRUTH for effect capability values.
    Replaces magic strings in handler capability constants.

    Using an enum instead of raw strings:
    - Prevents typos ("filesystem" vs "file_system")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes capability definitions
    - Preserves full type safety

    Capabilities:
        HTTP: HTTP/REST API interactions
        DB: Database operations (SQL, NoSQL)
        KAFKA: Apache Kafka message queue operations
        FILESYSTEM: File system read/write operations

    Example:
        >>> from omnibase_core.enums import EnumEffectCapability
        >>> cap = EnumEffectCapability.HTTP
        >>> str(cap)
        'http'
        >>> cap.value
        'http'
    """

    HTTP = "http"
    """HTTP/REST API interactions."""

    DB = "db"
    """Database operations (SQL, NoSQL)."""

    KAFKA = "kafka"
    """Apache Kafka message queue operations."""

    FILESYSTEM = "filesystem"
    """File system read/write operations."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

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

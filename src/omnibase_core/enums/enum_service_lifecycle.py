"""
Service Lifecycle Enum.

Defines service lifecycle patterns for dependency injection containers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumServiceLifecycle"]


@unique
class EnumServiceLifecycle(StrValueHelper, str, Enum):
    """Service lifecycle patterns for DI container.

    Controls how service instances are created, cached, and disposed
    within the dependency injection container.

    Values:
        SINGLETON: Single instance shared across all requests.
        TRANSIENT: New instance created for each request.
        SCOPED: Single instance per scope/request context.
        POOLED: Instance drawn from a pre-allocated pool.
        LAZY: Instance created on first access.
        EAGER: Instance created at container initialization.
    """

    SINGLETON = "singleton"
    """Single instance shared across all requests."""

    TRANSIENT = "transient"
    """New instance created for each request."""

    SCOPED = "scoped"
    """Single instance per scope/request context."""

    POOLED = "pooled"
    """Instance drawn from a pre-allocated pool."""

    LAZY = "lazy"
    """Instance created on first access."""

    EAGER = "eager"
    """Instance created at container initialization."""

"""
Injection Scope Enum.

Defines injection scope patterns for dependency injection containers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumInjectionScope"]


@unique
class EnumInjectionScope(StrValueHelper, str, Enum):
    """Injection scope patterns for DI container.

    Defines the scope boundaries within which service instances
    are shared or isolated.

    Values:
        REQUEST: Instance scoped to a single HTTP/RPC request.
        SESSION: Instance scoped to a user session.
        THREAD: Instance scoped to a single thread.
        PROCESS: Instance scoped to a single process.
        GLOBAL: Instance shared globally across the application.
        CUSTOM: Custom scope with user-defined boundaries.
    """

    REQUEST = "request"
    """Instance scoped to a single HTTP/RPC request."""

    SESSION = "session"
    """Instance scoped to a user session."""

    THREAD = "thread"
    """Instance scoped to a single thread."""

    PROCESS = "process"
    """Instance scoped to a single process."""

    GLOBAL = "global"
    """Instance shared globally across the application."""

    CUSTOM = "custom"
    """Custom scope with user-defined boundaries."""

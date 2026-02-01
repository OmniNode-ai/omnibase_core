"""
Registration Status Enum.

Defines status values for service registration operations in DI containers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumRegistrationStatus"]


@unique
class EnumRegistrationStatus(StrValueHelper, str, Enum):
    """Service registration status values.

    Indicates the outcome of attempting to register a service
    with the dependency injection container.

    Values:
        REGISTERED: Service was successfully registered.
        UNREGISTERED: Service was successfully unregistered.
        FAILED: Registration failed for an unspecified reason.
        PENDING: Registration is pending completion.
        CONFLICT: Registration failed due to naming conflict.
        INVALID: Registration failed due to invalid configuration.
    """

    REGISTERED = "registered"
    """Service was successfully registered."""

    UNREGISTERED = "unregistered"
    """Service was successfully unregistered."""

    FAILED = "failed"
    """Registration failed for an unspecified reason."""

    PENDING = "pending"
    """Registration is pending completion."""

    CONFLICT = "conflict"
    """Registration failed due to naming conflict."""

    INVALID = "invalid"
    """Registration failed due to invalid configuration."""

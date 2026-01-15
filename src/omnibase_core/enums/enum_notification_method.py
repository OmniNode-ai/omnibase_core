"""
Notification Method Enumeration.

HTTP methods for webhook notifications in ONEX infrastructure.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNotificationMethod(StrValueHelper, str, Enum):
    """Enumeration for HTTP notification methods used in webhook communications."""

    # Standard HTTP methods for webhook notifications
    POST = "POST"  # Standard webhook notification method
    PUT = "PUT"  # Update-style notifications
    PATCH = "PATCH"  # Partial update notifications
    GET = "GET"  # Query-style notifications (less common)


__all__ = ["EnumNotificationMethod"]

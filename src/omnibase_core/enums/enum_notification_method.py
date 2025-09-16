"""
Notification Method Enumeration.

HTTP methods for webhook notifications in ONEX infrastructure.
"""

from enum import Enum


class EnumNotificationMethod(str, Enum):
    """Enumeration for HTTP notification methods used in webhook communications."""

    # Standard HTTP methods for webhook notifications
    POST = "POST"  # Standard webhook notification method
    PUT = "PUT"  # Update-style notifications
    PATCH = "PATCH"  # Partial update notifications
    GET = "GET"  # Query-style notifications (less common)

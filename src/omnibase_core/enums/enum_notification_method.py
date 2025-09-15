"""
Notification Method Enum

HTTP methods supported for webhook notification delivery.
"""

from enum import Enum


class EnumNotificationMethod(str, Enum):
    """
    HTTP methods supported for webhook notification delivery.

    Defines the allowed HTTP methods for sending webhook notifications
    in the ONEX infrastructure notification system.
    """

    POST = "POST"
    PUT = "PUT"

    def __str__(self) -> str:
        """Return the string value of the method."""
        return self.value

    def is_post(self) -> bool:
        """Check if this is a POST method."""
        return self == self.POST

    def is_put(self) -> bool:
        """Check if this is a PUT method."""
        return self == self.PUT

#!/usr/bin/env python3
"""Invalid naming example - should trigger violations."""

from enum import Enum

from pydantic import BaseModel


# BAD: Should be ModelUserData
class UserData(BaseModel):
    """User data without proper naming."""

    user_id: str
    username: str


# BAD: Should be EnumStatusType
class StatusType(str, Enum):
    """Status enumeration without proper naming."""

    ACTIVE = "active"
    INACTIVE = "inactive"


# BAD: Should be ProtocolEventHandler
class EventHandler:
    """Protocol interface without proper naming."""

    def handle_event(self, event: dict) -> bool:
        return True

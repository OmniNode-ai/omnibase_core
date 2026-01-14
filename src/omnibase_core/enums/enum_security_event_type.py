"""
Security Event Type Enumeration.

Strongly typed enumeration for security event types.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSecurityEventType(StrValueHelper, str, Enum):
    """Enumeration for security event types."""

    # Authentication events
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILED = "authentication_failed"

    # Authorization events
    AUTHORIZATION_SUCCESS = "authorization_success"
    AUTHORIZATION_FAILED = "authorization_failed"

    # Tool access events
    TOOL_ACCESS = "tool_access"
    TOOL_ACCESS_DENIED = "tool_access_denied"

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_TERMINATED = "session_terminated"

    # Security violations
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # Administrative events
    POLICY_VIOLATION = "policy_violation"
    CONFIGURATION_CHANGE = "configuration_change"


__all__ = ["EnumSecurityEventType"]

"""Event types for Kafka messages."""

from enum import Enum


class EnumProxyEventType(str, Enum):
    """Event types for Kafka messages."""

    USER_MESSAGE_CAPTURED = "user_message_captured"
    CONTEXT_ANALYSIS_READY = "context_analysis_ready"
    SECURITY_VALIDATION_REQUIRED = "security_validation_required"
    CLAUDE_RESPONSE = "claude_response"

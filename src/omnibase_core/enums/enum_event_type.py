"""
Event Type Enum.

Strongly typed enumeration for event categories and routing.
Replaces string literals for event type discrimination.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEventType(StrValueHelper, str, Enum):
    """
    Strongly typed event categories for proper routing and handling.

    Used for event discrimination in event-driven architectures.
    Inherits from str for JSON serialization compatibility while
    providing type safety and IDE support.
    """

    SYSTEM = "system"
    USER = "user"
    WORKFLOW = "workflow"
    ERROR = "error"

    @classmethod
    def is_user_initiated(cls, event_type: EnumEventType) -> bool:
        """Check if the event type is user-initiated."""
        return event_type == cls.USER

    @classmethod
    def is_system_generated(cls, event_type: EnumEventType) -> bool:
        """Check if the event type is system-generated."""
        return event_type in {cls.SYSTEM, cls.WORKFLOW}

    @classmethod
    def requires_error_handling(cls, event_type: EnumEventType) -> bool:
        """Check if the event type requires special error handling."""
        return event_type == cls.ERROR

    @classmethod
    def is_workflow_related(cls, event_type: EnumEventType) -> bool:
        """Check if the event type is workflow-related."""
        return event_type == cls.WORKFLOW

    @classmethod
    def get_severity_level(cls, event_type: EnumEventType) -> str:
        """Get the default severity level for the event type."""
        severity_levels = {
            cls.SYSTEM: "info",
            cls.USER: "info",
            cls.WORKFLOW: "debug",
            cls.ERROR: "error",
        }
        return severity_levels.get(event_type, "info")

    @classmethod
    def get_routing_priority(cls, event_type: EnumEventType) -> str:
        """Get the routing priority for the event type."""
        priorities = {
            cls.SYSTEM: "normal",
            cls.USER: "high",
            cls.WORKFLOW: "normal",
            cls.ERROR: "critical",
        }
        return priorities.get(event_type, "normal")

    @classmethod
    def get_event_description(cls, event_type: EnumEventType) -> str:
        """Get a human-readable description of the event type."""
        descriptions = {
            cls.SYSTEM: "System-level events and notifications",
            cls.USER: "User-initiated actions and requests",
            cls.WORKFLOW: "Workflow execution and orchestration events",
            cls.ERROR: "Error conditions and exception events",
        }
        return descriptions.get(event_type, "Unknown event type")


# Export for use
__all__ = ["EnumEventType"]

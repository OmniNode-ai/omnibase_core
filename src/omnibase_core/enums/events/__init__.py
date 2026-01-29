"""Event-related enumerations.

Contains enums for event system types and lifecycle states.
"""

from omnibase_core.enums.events.enum_deregistration_reason import (
    EnumDeregistrationReason,
    is_planned_deregistration,
)

__all__ = ["EnumDeregistrationReason", "is_planned_deregistration"]

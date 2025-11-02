from __future__ import annotations

"""
Execution Trigger Enum.

Strongly typed execution trigger values for configuration - defines WHEN/HOW execution is initiated.
"""


from enum import Enum, unique


@unique
class EnumExecutionTrigger(str, Enum):
    """
    Execution trigger mode - WHEN/HOW execution is initiated.

    Defines scheduling and triggering mechanisms for execution:
    - AUTO: Automatic execution based on conditions
    - MANUAL: Manual user-initiated execution
    - SCHEDULED: Time-based scheduled execution
    - TRIGGER_BASED: Event-based triggered execution
    """

    AUTO = "auto"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    TRIGGER_BASED = "trigger_based"


# Export for use
__all__ = ["EnumExecutionTrigger"]

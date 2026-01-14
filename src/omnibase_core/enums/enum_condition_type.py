"""
Condition Type Enum.

Type of condition evaluation for workflow conditions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConditionType(StrValueHelper, str, Enum):
    """Type of condition evaluation."""

    WORKFLOW_STATE = "workflow_state"
    OUTPUT_VALUE = "output_value"
    EXECUTION_STATUS = "execution_status"
    TIME_BASED = "time_based"
    CUSTOM_EXPRESSION = "custom_expression"


__all__ = ["EnumConditionType"]

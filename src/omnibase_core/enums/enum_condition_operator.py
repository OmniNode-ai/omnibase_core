"""
Condition Operator Enum.

Allowed operators for workflow condition evaluation.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConditionOperator(StrValueHelper, str, Enum):
    """Allowed operators for workflow condition evaluation."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


__all__ = ["EnumConditionOperator"]

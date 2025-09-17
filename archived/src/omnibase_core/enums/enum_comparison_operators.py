# Enum for comparison operators
# DO NOT EDIT MANUALLY - regenerate using enum generation tools

from enum import Enum


class EnumComparisonOperators(str, Enum):
    """Enum for comparison operators used in conditional logic."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"

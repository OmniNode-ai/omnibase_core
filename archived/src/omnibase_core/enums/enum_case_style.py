"""
Enum for case style types supported by ONEX.

Defines all supported case styles for string conversion operations.
"""

from enum import Enum


class EnumCaseStyle(str, Enum):
    """Enum for case style types."""

    PASCAL_CASE = "pascal_case"
    SNAKE_CASE = "snake_case"
    CAMEL_CASE = "camel_case"
    KEBAB_CASE = "kebab_case"
    SCREAMING_SNAKE_CASE = "screaming_snake_case"
    ENUM_MEMBER_NAME = "enum_member_name"

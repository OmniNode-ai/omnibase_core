"""
Validation rules input type enumeration.

Defines types for discriminated union in validation rules input structures.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationRulesInputType(StrValueHelper, str, Enum):
    """Validation rules input type enumeration for discriminated unions."""

    NONE = "none"
    DICT_OBJECT = "dict_object"
    MODEL_VALIDATION_RULES = "model_validation_rules"
    STRING = "string"


# Export for use
__all__ = ["EnumValidationRulesInputType"]

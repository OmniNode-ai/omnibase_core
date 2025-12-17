from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.enums.enum_validation_value_type import EnumValidationValueType

"""
TypedDict for ModelValidationValue.serialize() return type.

This module defines the structure returned by ModelValidationValue's serialize method,
providing type-safe dictionary representation for validation values.
"""


class TypedDictValidationValueSerialized(TypedDict):
    """TypedDict for serialized ModelValidationValue.

    Fields match the ModelValidationValue model fields, with enum types
    represented as their serialized forms when use_enum_values=False.
    """

    value_type: EnumValidationValueType
    raw_value: object


__all__ = [
    "TypedDictValidationValueSerialized",
]

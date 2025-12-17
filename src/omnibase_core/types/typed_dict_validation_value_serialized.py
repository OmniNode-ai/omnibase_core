from __future__ import annotations

from typing import TypedDict

"""
TypedDict for ModelValidationValue.serialize() return type.

This module defines the structure returned by ModelValidationValue's serialize method,
providing type-safe dictionary representation for validation values.
"""


class TypedDictValidationValueSerialized(TypedDict):
    """TypedDict for serialized ModelValidationValue.

    Fields match the ModelValidationValue model fields. Since
    EnumValidationValueType is a StrEnum (str, Enum), it serializes to its
    string value in model_dump() output for consistency with
    TypedDictModelValueSerialized.
    """

    value_type: str
    raw_value: object


__all__ = [
    "TypedDictValidationValueSerialized",
]

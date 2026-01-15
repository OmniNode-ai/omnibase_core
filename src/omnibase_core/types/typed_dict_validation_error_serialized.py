from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from omnibase_core.types.typed_dict_validation_value_serialized import (
    TypedDictValidationValueSerialized,
)

if TYPE_CHECKING:
    from uuid import UUID

"""
TypedDict for ModelValidationError.serialize() return type.

This module defines the structure returned by ModelValidationError's serialize method,
providing type-safe dictionary representation for validation errors.
"""


class TypedDictValidationErrorSerialized(TypedDict):
    """TypedDict for serialized ModelValidationError.

    All fields match the ModelValidationError model fields. Since
    EnumSeverity is a StrEnum (str, Enum), it serializes to its
    string value in model_dump() output. UUID fields retain their UUID type
    in Python mode.
    """

    message: str
    severity: str
    field_id: UUID | None
    field_display_name: str | None
    error_code: str | None
    details: dict[str, TypedDictValidationValueSerialized] | None
    line_number: int | None
    column_number: int | None


__all__ = [
    "TypedDictValidationErrorSerialized",
]

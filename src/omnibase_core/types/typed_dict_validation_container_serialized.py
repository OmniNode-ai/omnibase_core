from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_validation_error_serialized import (
        TypedDictValidationErrorSerialized,
    )

"""
TypedDict for ModelValidationContainer.serialize() return type.

This module defines the structure returned by ModelValidationContainer's serialize method,
providing type-safe dictionary representation for validation containers.
"""


class TypedDictValidationContainerSerialized(TypedDict):
    """TypedDict for serialized ModelValidationContainer.

    Fields match the ModelValidationContainer model fields. Both errors and
    warnings have default_factory=list in the model, so they are always
    present in the serialization output (as empty lists when not set).
    Since serialize() uses exclude_none=False, all fields are always present.
    """

    errors: list[TypedDictValidationErrorSerialized]
    warnings: list[str]


__all__ = [
    "TypedDictValidationContainerSerialized",
]

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_validation_container_serialized import (
        TypedDictValidationContainerSerialized,
    )

"""
TypedDict for ModelValidationBase.serialize() return type.

This module defines the structure returned by ModelValidationBase's serialize method,
providing type-safe dictionary representation for validation base models.
"""


class TypedDictValidationBaseSerialized(TypedDict):
    """TypedDict for serialized ModelValidationBase.

    Fields match the ModelValidationBase model fields.
    """

    validation: TypedDictValidationContainerSerialized


__all__ = [
    "TypedDictValidationBaseSerialized",
]

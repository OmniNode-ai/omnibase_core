"""
TypedDict for custom fields dictionary representation.

Used for type-safe access to ModelCustomFields.field_values.
"""

from typing import TypedDict


class TypedDictCustomFieldsDict(TypedDict, total=False):
    """
    TypedDict for custom fields dictionary.

    Used for type-safe representation of ModelCustomFields.field_values,
    which is a flexible dictionary with string keys and arbitrary values.

    This TypedDict is intentionally permissive (total=False, empty body)
    to accommodate the extensible nature of custom fields.
    """


# Type alias for the flexible custom fields type
CustomFieldsDict = TypedDictCustomFieldsDict


__all__ = ["TypedDictCustomFieldsDict", "CustomFieldsDict"]

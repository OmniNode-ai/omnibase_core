"""
TypedDict for custom fields dictionary representation.

Used by ModelCustomFields.to_dict() method.
"""

from typing import TypedDict


class TypedDictCustomFieldsDict(TypedDict, total=False):
    """
    TypedDict for custom fields dictionary.

    Used for ModelCustomFields.to_dict() return type.

    The to_dict() method returns a copy of field_values, which is a flexible
    dictionary with string keys and arbitrary values. This TypedDict is
    intentionally permissive to accommodate the extensible nature of custom fields.

    Note: The actual return is field_values.copy() which has type dict[str, Any],
    but we use TypedDict with total=False to indicate this is a flexible mapping
    while still providing type safety.
    """


# Type alias for the flexible custom fields return type
# Since custom fields can contain any key-value pairs, we use a TypedDict
# with no required fields (total=False and empty body)
CustomFieldsDict = TypedDictCustomFieldsDict


__all__ = ["TypedDictCustomFieldsDict", "CustomFieldsDict"]

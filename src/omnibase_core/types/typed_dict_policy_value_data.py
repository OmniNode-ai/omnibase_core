# ONEX-EXEMPT: typed-dict-collection - Data (output) and Input types serve different purposes
"""
TypedDict for policy value data structures.

Used by ModelPolicyValue.infer_value_type() and as_dict() methods.
"""

from typing import Literal, TypedDict


class TypedDictPolicyValueData(TypedDict, total=True):
    """
    TypedDict for policy value dictionary representation.

    Used for:
    - ModelPolicyValue.infer_value_type() return type (input data structure)
    - ModelPolicyValue.as_dict() return type

    Attributes:
        value: The actual policy value (supports None, bool, int, float, str, list, dict)
        value_type: Type discriminator for the value
        is_sensitive: Flag indicating if value contains sensitive data
        metadata: Optional string metadata for audit and tracking
    """

    value: None | bool | int | float | str | list[object] | dict[str, object]
    value_type: Literal["none", "bool", "int", "float", "str", "list", "dict"]
    is_sensitive: bool
    metadata: dict[str, str]


class TypedDictPolicyValueInput(TypedDict, total=False):
    """
    TypedDict for policy value input before validation.

    Used for ModelPolicyValue.infer_value_type() input - value_type is optional
    as it may be inferred from the value.

    Attributes:
        value: The actual policy value (required)
        value_type: Type discriminator (optional - may be inferred)
        is_sensitive: Flag for sensitive data (optional)
        metadata: Optional metadata (optional)
    """

    value: None | bool | int | float | str | list[object] | dict[str, object]
    value_type: Literal["none", "bool", "int", "float", "str", "list", "dict"]
    is_sensitive: bool
    metadata: dict[str, str]


__all__ = ["TypedDictPolicyValueData", "TypedDictPolicyValueInput"]

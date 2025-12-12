"""
TypedDict for model class information extracted from AST.

Used by contract_validator.py to represent Pydantic model class definitions.
"""

from typing import TypedDict

from omnibase_core.types.typed_dict_model_field_info import TypedDictModelFieldInfo


class TypedDictModelClassInfo(TypedDict):
    """
    Represents a Pydantic model class definition extracted from AST.

    Attributes:
        name: The class name (e.g., "ModelEffectInput")
        fields: List of field definitions with name and type info
        bases: List of base class names as strings (e.g., ["BaseModel"])
    """

    name: str
    fields: list[TypedDictModelFieldInfo]
    bases: list[str]


__all__ = ["TypedDictModelClassInfo"]

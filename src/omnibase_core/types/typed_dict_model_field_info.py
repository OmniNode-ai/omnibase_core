"""
TypedDict for model field information extracted from AST.

Used by contract_validator.py to represent field definitions from Pydantic models.
"""

from typing import TypedDict


class TypedDictModelFieldInfo(TypedDict):
    """
    Represents a field definition extracted from a Pydantic model class.

    Attributes:
        name: The field name identifier
        type: The type annotation as a string (e.g., "str", "int", "list[str]")
    """

    name: str
    type: str


__all__ = ["TypedDictModelFieldInfo"]

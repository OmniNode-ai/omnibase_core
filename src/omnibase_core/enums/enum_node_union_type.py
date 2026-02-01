"""
Node Union Type Enum.

Strongly typed enumeration for node union type discriminators.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeUnionType(StrValueHelper, str, Enum):
    """
    Strongly typed node union type discriminators.

    Used for discriminated union patterns in function node type handling.
    Replaces Union[ModelFunctionNode, ModelFunctionNodeData] patterns
    with structured typing.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    FUNCTION_NODE = "function_node"
    FUNCTION_NODE_DATA = "function_node_data"

    @classmethod
    def is_function_node(cls, node_type: EnumNodeUnionType) -> bool:
        """Check if the node type represents a function node."""
        return node_type == cls.FUNCTION_NODE

    @classmethod
    def is_function_node_data(cls, node_type: EnumNodeUnionType) -> bool:
        """Check if the node type represents function node data."""
        return node_type == cls.FUNCTION_NODE_DATA

    @classmethod
    def is_node_related(cls, node_type: EnumNodeUnionType) -> bool:
        """Check if the node type is related to function nodes."""
        # Future-proof: derive from all enum members
        return node_type in set(cls)

    @classmethod
    def get_all_node_types(cls) -> list[EnumNodeUnionType]:
        """Get all node union types."""
        # Future-proof: derive from all enum members
        return list(cls)


# Export for use
__all__ = ["EnumNodeUnionType"]

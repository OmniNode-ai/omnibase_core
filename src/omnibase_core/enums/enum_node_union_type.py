"""
Node Union Type Enum.

Strongly typed enumeration for node union type discriminators.
"""

from __future__ import annotations

from enum import Enum


class EnumNodeUnionType(str, Enum):
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

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

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
        return node_type in {cls.FUNCTION_NODE, cls.FUNCTION_NODE_DATA}

    @classmethod
    def get_all_node_types(cls) -> list[EnumNodeUnionType]:
        """Get all node union types."""
        return [cls.FUNCTION_NODE, cls.FUNCTION_NODE_DATA]


# Export for use
__all__ = ["EnumNodeUnionType"]

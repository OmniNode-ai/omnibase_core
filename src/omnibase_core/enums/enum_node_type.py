"""
Node Type Enum.

Strongly typed node type values for ONEX architecture node classification.
"""

from __future__ import annotations

from enum import Enum


class EnumNodeType(str, Enum):
    """
    Strongly typed node type values for ONEX architecture.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for node classification operations.
    """

    # Core ONEX node types
    COMPUTE = "COMPUTE"
    GATEWAY = "GATEWAY"
    ORCHESTRATOR = "ORCHESTRATOR"
    REDUCER = "REDUCER"
    EFFECT = "EFFECT"
    VALIDATOR = "VALIDATOR"
    TRANSFORMER = "TRANSFORMER"
    AGGREGATOR = "AGGREGATOR"

    # Generic node types (lowercase for legacy compatibility)
    FUNCTION = "function"
    TOOL = "tool"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"
    WORKFLOW = "workflow"
    SERVICE = "service"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_processing_node(cls, node_type: EnumNodeType) -> bool:
        """Check if the node type performs data processing."""
        return node_type in {
            cls.COMPUTE,
            cls.TRANSFORMER,
            cls.AGGREGATOR,
            cls.REDUCER,
        }

    @classmethod
    def is_control_node(cls, node_type: EnumNodeType) -> bool:
        """Check if the node type handles control flow."""
        return node_type in {
            cls.ORCHESTRATOR,
            cls.GATEWAY,
            cls.VALIDATOR,
        }

    @classmethod
    def is_output_node(cls, node_type: EnumNodeType) -> bool:
        """Check if the node type produces output effects."""
        return node_type in {
            cls.EFFECT,
            cls.AGGREGATOR,
        }

    @classmethod
    def get_node_category(cls, node_type: EnumNodeType) -> str:
        """Get the functional category of a node type."""
        if cls.is_processing_node(node_type):
            return "processing"
        elif cls.is_control_node(node_type):
            return "control"
        elif cls.is_output_node(node_type):
            return "output"
        else:
            return "unknown"


# Export for use
__all__ = ["EnumNodeType"]
from __future__ import annotations

"""
Node Type Enum.

Strongly typed node type values for ONEX architecture node classification.
"""


from enum import Enum, unique


@unique
class EnumNodeType(str, Enum):
    """
    Specific node implementation types for ONEX architecture.

    EnumNodeType represents the specific KIND OF IMPLEMENTATION a node uses,
    defining its concrete behavior, capabilities, and implementation pattern.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for node classification operations.

    Relationship to EnumNodeKind
    -----------------------------
    - **EnumNodeType** (this enum): Specific node implementation type
      - Answers: "What specific kind of node implementation is this?"
      - Example: TRANSFORMER, AGGREGATOR, VALIDATOR (specific implementations)
      - Use when: Node discovery, capability matching, specific behavior selection

    - **EnumNodeKind**: High-level architectural classification
      - Answers: "What role does this node play in the ONEX workflow?"
      - Example: COMPUTE (data processing role)
      - Use when: Routing data through the ONEX pipeline, enforcing architectural patterns

    Multiple EnumNodeType values can map to a single EnumNodeKind. For example:
    - TRANSFORMER, AGGREGATOR, COMPUTE_GENERIC → All are COMPUTE kind
    - GATEWAY, VALIDATOR → Both are control flow nodes (ORCHESTRATOR kind)

    For high-level architectural classification, see EnumNodeKind.
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

    # Generic node types
    FUNCTION = "FUNCTION"
    TOOL = "TOOL"
    AGENT = "AGENT"
    MODEL = "MODEL"
    PLUGIN = "PLUGIN"
    SCHEMA = "SCHEMA"
    NODE = "NODE"
    WORKFLOW = "WORKFLOW"
    SERVICE = "SERVICE"
    COMPUTE_GENERIC = "COMPUTE_GENERIC"  # Generic compute node type
    UNKNOWN = "UNKNOWN"

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
        if cls.is_control_node(node_type):
            return "control"
        if cls.is_output_node(node_type):
            return "output"
        return "unknown"


# Export for use
__all__ = ["EnumNodeType"]

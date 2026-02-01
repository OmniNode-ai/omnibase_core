"""
Node ModelArchitecture Type Enum.

Strongly typed enumeration for ONEX 4-node architecture classifications.
Replaces Literal["orchestrator", "compute", "reducer", "effect"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeArchitectureType(StrValueHelper, str, Enum):
    """
    Strongly typed 4-node architecture type discriminators.

    Used for ONEX architecture node classification following the 4-node pattern.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    ORCHESTRATOR = "orchestrator"
    COMPUTE = "compute"
    REDUCER = "reducer"
    EFFECT = "effect"

    @classmethod
    def is_processing_node(cls, node_type: EnumNodeArchitectureType) -> bool:
        """Check if the node type performs data processing."""
        return node_type in {cls.COMPUTE, cls.REDUCER}

    @classmethod
    def is_control_node(cls, node_type: EnumNodeArchitectureType) -> bool:
        """Check if the node type handles control flow."""
        return node_type == cls.ORCHESTRATOR

    @classmethod
    def is_output_node(cls, node_type: EnumNodeArchitectureType) -> bool:
        """Check if the node type produces output effects."""
        return node_type == cls.EFFECT

    @classmethod
    def get_node_purpose(cls, node_type: EnumNodeArchitectureType) -> str:
        """Get the primary purpose of a node type."""
        purposes = {
            cls.ORCHESTRATOR: "workflow coordination and control flow",
            cls.COMPUTE: "data processing and business logic",
            cls.REDUCER: "state management and data aggregation",
            cls.EFFECT: "external interactions and side effects",
        }
        return purposes.get(node_type, "unknown")

    @classmethod
    def get_typical_responsibilities(
        cls,
        node_type: EnumNodeArchitectureType,
    ) -> list[str]:
        """Get typical responsibilities for a node type."""
        responsibilities = {
            cls.ORCHESTRATOR: [
                "Coordinate workflow steps",
                "Manage execution flow",
                "Handle error recovery",
                "Route between nodes",
            ],
            cls.COMPUTE: [
                "Process business logic",
                "Transform data",
                "Perform calculations",
                "Apply rules and algorithms",
            ],
            cls.REDUCER: [
                "Aggregate results",
                "Manage state transitions",
                "Consolidate data",
                "Maintain consistency",
            ],
            cls.EFFECT: [
                "Interact with external systems",
                "Produce side effects",
                "Handle I/O operations",
                "Manage user interfaces",
            ],
        }
        return responsibilities.get(node_type, [])


# Export for use
__all__ = ["EnumNodeArchitectureType"]

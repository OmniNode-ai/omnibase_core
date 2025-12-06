from __future__ import annotations

"""
Node Kind Enum.

Types of ONEX nodes in the four-node architecture.
"""

from enum import Enum, unique


@unique
class EnumNodeKind(str, Enum):
    """
    High-level architectural classification for ONEX nodes.

    EnumNodeKind represents the architectural ROLE a node plays in the ONEX
    workflow, defining WHERE it fits in the data flow and WHAT architectural
    responsibility it fulfills.

    The ONEX four-node architecture defines four core node types that form
    a unidirectional data flow: EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR.

    Additionally, RUNTIME_HOST represents nodes that host and coordinate
    the execution of other nodes within the ONEX runtime environment.

    Relationship to EnumNodeType
    -----------------------------
    - **EnumNodeKind** (this enum): High-level architectural classification
      - Answers: "What role does this node play in the ONEX workflow?"
      - Example: COMPUTE (data processing role)
      - Use when: Routing data through the ONEX pipeline, enforcing architectural patterns

    - **EnumNodeType**: Specific node implementation type
      - Answers: "What specific kind of node implementation is this?"
      - Example: TRANSFORMER, AGGREGATOR, VALIDATOR (specific compute implementations)
      - Use when: Node discovery, capability matching, specific behavior selection

    A single EnumNodeKind (e.g., COMPUTE) can have multiple EnumNodeType implementations
    (e.g., TRANSFORMER, AGGREGATOR, COMPUTE_GENERIC).

    For specific node implementation types, see EnumNodeType.

    Example:
        >>> # Classify a node
        >>> node_kind = EnumNodeKind.COMPUTE
        >>> EnumNodeKind.is_core_node_type(node_kind)
        True

        >>> # Check infrastructure type
        >>> EnumNodeKind.is_infrastructure_type(EnumNodeKind.RUNTIME_HOST)
        True

        >>> # Use with Pydantic (string coercion works)
        >>> from pydantic import BaseModel
        >>> class NodeConfig(BaseModel):
        ...     kind: EnumNodeKind
        >>> config = NodeConfig(kind="compute")  # String automatically coerced
        >>> config.kind == EnumNodeKind.COMPUTE
        True

        >>> # String serialization
        >>> str(EnumNodeKind.EFFECT)
        'effect'

        >>> # Node type classification
        >>> node_types = [EnumNodeKind.COMPUTE, EnumNodeKind.RUNTIME_HOST]
        >>> core_nodes = [n for n in node_types if EnumNodeKind.is_core_node_type(n)]
        >>> len(core_nodes)
        1
    """

    # Core four-node architecture types
    EFFECT = "effect"
    """External interactions (I/O): API calls, database ops, file system, message queues."""

    COMPUTE = "compute"
    """Data processing & transformation: calculations, validations, data mapping."""

    REDUCER = "reducer"
    """State aggregation & management: state machines, accumulators, event reduction."""

    ORCHESTRATOR = "orchestrator"
    """Workflow coordination: multi-step workflows, parallel execution, error recovery."""

    # Runtime infrastructure type
    RUNTIME_HOST = "runtime_host"
    """Runtime host nodes that manage node lifecycle and execution coordination."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_core_node_type(cls, node_kind: EnumNodeKind) -> bool:
        """
        Check if the node kind is one of the core four-node architecture types.

        Args:
            node_kind: The node kind to check

        Returns:
            True if it's a core node type, False otherwise
        """
        return node_kind in {cls.EFFECT, cls.COMPUTE, cls.REDUCER, cls.ORCHESTRATOR}

    @classmethod
    def is_infrastructure_type(cls, node_kind: EnumNodeKind) -> bool:
        """
        Check if the node kind is an infrastructure type.

        Args:
            node_kind: The node kind to check

        Returns:
            True if it's an infrastructure type, False otherwise
        """
        return node_kind == cls.RUNTIME_HOST


# Export for use
__all__ = ["EnumNodeKind"]

from __future__ import annotations

"""
Node Kind Enum.

Types of ONEX nodes in the four-node architecture.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeKind(StrValueHelper, str, Enum):
    """
    High-level architectural classification for ONEX four-node architecture.

    Values: EFFECT (I/O), COMPUTE (transform), REDUCER (state), ORCHESTRATOR (workflow),
    RUNTIME_HOST (infrastructure). Data flows: EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR.
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

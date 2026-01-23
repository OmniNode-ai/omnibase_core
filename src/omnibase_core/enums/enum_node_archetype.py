"""
Node Archetype Enum.

Design-time architectural role classification for handler contracts.

Defines the 4 core archetype values used in handler contracts to specify
the node's role in the ONEX workflow: COMPUTE, EFFECT, REDUCER, ORCHESTRATOR.

This enum is distinct from EnumNodeKind which includes infrastructure types
like RUNTIME_HOST. EnumNodeArchetype is specifically for contract-level
classification where only the four core node types are valid.

Related:
    - OMN-1465: Rename handler_kind to node_archetype
    - EnumNodeKind: Runtime node classification (includes RUNTIME_HOST)
    - ModelHandlerBehavior: Uses this enum for contract-level handler roles

.. versionadded:: 0.9.2
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = [
    "EnumNodeArchetype",
]


@unique
class EnumNodeArchetype(StrValueHelper, str, Enum):
    """
    Design-time architectural role for handler contracts.

    Values: COMPUTE (transform), EFFECT (I/O), REDUCER (state), ORCHESTRATOR (workflow).
    Used in handler contracts to specify the node's architectural role.

    Unlike EnumNodeKind, this enum does NOT include RUNTIME_HOST since
    contracts cannot declare themselves as runtime infrastructure.

    Example:
        >>> archetype = EnumNodeArchetype.COMPUTE
        >>> str(archetype)
        'compute'
        >>> archetype == "compute"
        True
    """

    COMPUTE = "compute"
    """Pure data transformation: calculations, validations, data mapping."""

    EFFECT = "effect"
    """External I/O operations: API calls, database ops, file system access."""

    REDUCER = "reducer"
    """State aggregation: FSM-driven state machines, event reduction."""

    ORCHESTRATOR = "orchestrator"
    """Workflow coordination: multi-step workflows, parallel execution."""

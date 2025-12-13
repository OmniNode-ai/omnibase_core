"""
Handler Capabilities Constants (OMN-169).

Centralized capability sets for handler type validation. This module provides:

1. Capability Constants - Immutable frozensets defining available capabilities
   for each node type in the ONEX four-node architecture.

2. Node Type Requirements - Mapping of EnumNodeKind to required capabilities
   that handlers must implement.

3. Validation Functions - Functions to validate requested vs available capabilities
   and to retrieve capabilities by node kind.

Design Principles:
    - Use frozenset for immutability (EFFECT_CAPABILITIES, etc.)
    - SCREAMING_SNAKE_CASE for constants
    - Clear error messages with capability name, node_type, available_capabilities
    - Raise UnsupportedCapabilityError when capability not available

VERSION: 1.1.0 - Now uses typed enums instead of magic strings

Author: ONEX Framework Team
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.enums.enum_compute_capability import EnumComputeCapability
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_capability import EnumEffectCapability
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.enums.enum_node_requirement import EnumNodeRequirement
from omnibase_core.enums.enum_orchestrator_capability import EnumOrchestratorCapability
from omnibase_core.enums.enum_reducer_capability import EnumReducerCapability
from omnibase_core.errors.exception_unsupported_capability_error import (
    UnsupportedCapabilityError,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

# ==============================================================================
# Capability Constants
# ==============================================================================

# EFFECT node capabilities: External interactions (I/O)
# API calls, database operations, file system access, message queues
EFFECT_CAPABILITIES: frozenset[str] = frozenset(
    {
        EnumEffectCapability.HTTP,
        EnumEffectCapability.DB,
        EnumEffectCapability.KAFKA,
        EnumEffectCapability.FILESYSTEM,
    }
)

# COMPUTE node capabilities: Data processing & transformation
# Calculations, validations, data mapping
COMPUTE_CAPABILITIES: frozenset[str] = frozenset(
    {
        EnumComputeCapability.TRANSFORM,
        EnumComputeCapability.VALIDATE,
    }
)

# REDUCER node capabilities: State aggregation & management
# State machines (FSM), accumulators, event reduction
REDUCER_CAPABILITIES: frozenset[str] = frozenset(
    {
        EnumReducerCapability.FSM_INTERPRETER,
    }
)

# ORCHESTRATOR node capabilities: Workflow coordination
# Multi-step workflows, parallel execution, error recovery
ORCHESTRATOR_CAPABILITIES: frozenset[str] = frozenset(
    {
        EnumOrchestratorCapability.WORKFLOW_RESOLVER,
    }
)


# ==============================================================================
# Node Type Requirements
# ==============================================================================

# Mapping of node kinds to their required handler capabilities.
# These are the minimum capabilities that handlers MUST implement
# for a given node type.
NODE_TYPE_REQUIREMENTS: dict[EnumNodeKind, frozenset[str]] = {
    EnumNodeKind.EFFECT: frozenset({EnumNodeRequirement.HANDLER_EXECUTE}),
    EnumNodeKind.COMPUTE: frozenset(),  # No required capabilities
    EnumNodeKind.REDUCER: frozenset({EnumNodeRequirement.FSM_INTERPRETER}),
    EnumNodeKind.ORCHESTRATOR: frozenset({EnumNodeRequirement.WORKFLOW_RESOLVER}),
}


# ==============================================================================
# Internal Mapping for get_capabilities_by_node_kind
# ==============================================================================

_NODE_KIND_TO_CAPABILITIES: dict[EnumNodeKind, frozenset[str]] = {
    EnumNodeKind.EFFECT: EFFECT_CAPABILITIES,
    EnumNodeKind.COMPUTE: COMPUTE_CAPABILITIES,
    EnumNodeKind.REDUCER: REDUCER_CAPABILITIES,
    EnumNodeKind.ORCHESTRATOR: ORCHESTRATOR_CAPABILITIES,
}


# ==============================================================================
# Validation Functions
# ==============================================================================


def validate_capabilities(
    requested: AbstractSet[str],
    available: AbstractSet[str],
    node_type: str,
) -> None:
    """
    Validate that all requested capabilities are available.

    This function checks each requested capability against the available set
    and raises UnsupportedCapabilityError if any capability is not available.

    Args:
        requested: Set of capabilities being requested
        available: Set of capabilities that are available
        node_type: String identifier for the node type (for error context)

    Returns:
        None if all requested capabilities are available

    Raises:
        UnsupportedCapabilityError: If any requested capability is not available.
            The error includes:
            - capability: The first missing capability found
            - node_type: The node type that lacks the capability
            - available_capabilities: List of available capabilities

    Example:
        >>> validate_capabilities(
        ...     requested={"http", "db"},
        ...     available={"http", "db", "kafka"},
        ...     node_type="EFFECT",
        ... )
        # Returns None - all capabilities available

        >>> validate_capabilities(
        ...     requested={"graphql"},
        ...     available={"http", "db"},
        ...     node_type="EFFECT",
        ... )
        # Raises UnsupportedCapabilityError
    """
    # Empty requested set is always valid
    if not requested:
        return

    # Find missing capabilities
    missing = requested - available

    if missing:
        # Report the first missing capability (sorted for deterministic behavior)
        first_missing = sorted(missing)[0]
        available_list = sorted(available)

        raise UnsupportedCapabilityError(
            message=(
                f"Capability '{first_missing}' is not available for node type "
                f"'{node_type}'. Available capabilities: {available_list}"
            ),
            error_code=EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR,
            capability=first_missing,
            node_type=node_type,
            available_capabilities=available_list,
        )

    return


def get_capabilities_by_node_kind(node_kind: EnumNodeKind) -> frozenset[str]:
    """
    Get the capability set for a given node kind.

    This function returns the frozenset of capabilities defined for
    the specified EnumNodeKind. RUNTIME_HOST is not a core node type
    and will raise ValueError.

    Args:
        node_kind: The EnumNodeKind to get capabilities for

    Returns:
        frozenset of capability strings for the node kind

    Raises:
        ValueError: If node_kind is RUNTIME_HOST (infrastructure type,
            not a core node type with defined capabilities)

    Example:
        >>> get_capabilities_by_node_kind(EnumNodeKind.EFFECT)
        frozenset({'http', 'db', 'kafka', 'filesystem'})

        >>> get_capabilities_by_node_kind(EnumNodeKind.RUNTIME_HOST)
        # Raises ValueError
    """
    if node_kind == EnumNodeKind.RUNTIME_HOST:
        raise ModelOnexError(
            message=(
                f"RUNTIME_HOST is an infrastructure type, not a core node type. "
                f"It does not have a defined capability set. "
                f"Use one of: {list(_NODE_KIND_TO_CAPABILITIES.keys())}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"node_kind": str(node_kind)},
        )

    if node_kind not in _NODE_KIND_TO_CAPABILITIES:
        raise ModelOnexError(
            message=(
                f"Unknown node kind: {node_kind}. "
                f"Expected one of: {list(_NODE_KIND_TO_CAPABILITIES.keys())}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"node_kind": str(node_kind)},
        )

    return _NODE_KIND_TO_CAPABILITIES[node_kind]


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    # Capability Enums (re-exported for convenience)
    "EnumComputeCapability",
    "EnumEffectCapability",
    "EnumNodeRequirement",
    "EnumOrchestratorCapability",
    "EnumReducerCapability",
    # Capability Constants
    "EFFECT_CAPABILITIES",
    "COMPUTE_CAPABILITIES",
    "REDUCER_CAPABILITIES",
    "ORCHESTRATOR_CAPABILITIES",
    # Node Type Requirements
    "NODE_TYPE_REQUIREMENTS",
    # Validation Functions
    "validate_capabilities",
    "get_capabilities_by_node_kind",
]

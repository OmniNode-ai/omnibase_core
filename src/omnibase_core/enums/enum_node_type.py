from __future__ import annotations

"""
Node Type Enum.

Strongly typed node type values for ONEX architecture node classification.
"""


from enum import Enum, unique
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from omnibase_core.enums.enum_node_kind import EnumNodeKind


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

    # Generic node types (one per EnumNodeKind)
    # These are the primary node types aligned with the ONEX 4-node architecture
    COMPUTE_GENERIC = "COMPUTE_GENERIC"  # Generic compute node type
    EFFECT_GENERIC = "EFFECT_GENERIC"  # Generic effect node type
    REDUCER_GENERIC = "REDUCER_GENERIC"  # Generic reducer node type
    ORCHESTRATOR_GENERIC = "ORCHESTRATOR_GENERIC"  # Generic orchestrator node type
    RUNTIME_HOST_GENERIC = "RUNTIME_HOST_GENERIC"  # Generic runtime host node type

    # Specific node implementation types
    GATEWAY = "GATEWAY"
    VALIDATOR = "VALIDATOR"
    TRANSFORMER = "TRANSFORMER"
    AGGREGATOR = "AGGREGATOR"

    # Specific node types
    FUNCTION = "FUNCTION"
    TOOL = "TOOL"
    AGENT = "AGENT"
    MODEL = "MODEL"
    PLUGIN = "PLUGIN"
    SCHEMA = "SCHEMA"
    NODE = "NODE"
    WORKFLOW = "WORKFLOW"
    SERVICE = "SERVICE"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_processing_node(cls, node_type: EnumNodeType) -> bool:
        """Check if the node type performs data processing."""
        return node_type in {
            cls.COMPUTE_GENERIC,
            cls.TRANSFORMER,
            cls.AGGREGATOR,
            cls.REDUCER_GENERIC,
        }

    @classmethod
    def is_control_node(cls, node_type: EnumNodeType) -> bool:
        """Check if the node type handles control flow."""
        return node_type in {
            cls.ORCHESTRATOR_GENERIC,
            cls.GATEWAY,
            cls.VALIDATOR,
        }

    @classmethod
    def is_output_node(cls, node_type: EnumNodeType) -> bool:
        """Check if the node type produces output effects."""
        return node_type in {
            cls.EFFECT_GENERIC,
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


# Note: _KIND_MAP is dynamically populated at module import time by _populate_kind_map()
# This declaration provides the initial empty dict that gets updated with mappings
# Type annotation: ClassVar[dict[EnumNodeType, EnumNodeKind]]
EnumNodeType._KIND_MAP = {}  # type: ignore[attr-defined]


def _populate_kind_map() -> None:
    """
    Populate the type-to-kind mapping with all EnumNodeType mappings.

    This function is called at module import time to populate EnumNodeType._KIND_MAP
    with the authoritative mapping of node types to architectural kinds.
    """
    from omnibase_core.enums.enum_node_kind import EnumNodeKind

    EnumNodeType._KIND_MAP.update(  # type: ignore[attr-defined]
        {
            # COMPUTE kind - data processing & transformation
            EnumNodeType.COMPUTE_GENERIC: EnumNodeKind.COMPUTE,
            EnumNodeType.TRANSFORMER: EnumNodeKind.COMPUTE,
            EnumNodeType.AGGREGATOR: EnumNodeKind.COMPUTE,
            EnumNodeType.FUNCTION: EnumNodeKind.COMPUTE,
            EnumNodeType.MODEL: EnumNodeKind.COMPUTE,
            # EFFECT kind - external interactions (I/O)
            EnumNodeType.EFFECT_GENERIC: EnumNodeKind.EFFECT,
            EnumNodeType.TOOL: EnumNodeKind.EFFECT,
            EnumNodeType.AGENT: EnumNodeKind.EFFECT,
            # REDUCER kind - state aggregation & management
            EnumNodeType.REDUCER_GENERIC: EnumNodeKind.REDUCER,
            # ORCHESTRATOR kind - workflow coordination
            EnumNodeType.ORCHESTRATOR_GENERIC: EnumNodeKind.ORCHESTRATOR,
            EnumNodeType.GATEWAY: EnumNodeKind.ORCHESTRATOR,
            EnumNodeType.VALIDATOR: EnumNodeKind.ORCHESTRATOR,
            EnumNodeType.WORKFLOW: EnumNodeKind.ORCHESTRATOR,
            # RUNTIME_HOST kind - runtime infrastructure
            EnumNodeType.RUNTIME_HOST_GENERIC: EnumNodeKind.RUNTIME_HOST,
            # Generic/unknown types - map to COMPUTE by default for backward compatibility
            EnumNodeType.PLUGIN: EnumNodeKind.COMPUTE,
            EnumNodeType.SCHEMA: EnumNodeKind.COMPUTE,
            EnumNodeType.NODE: EnumNodeKind.COMPUTE,
            EnumNodeType.SERVICE: EnumNodeKind.COMPUTE,
            EnumNodeType.UNKNOWN: EnumNodeKind.COMPUTE,
        }
    )


# Populate mapping immediately upon module import
_populate_kind_map()


# Add get_node_kind as a classmethod to EnumNodeType
@classmethod  # type: ignore[misc]
def _get_node_kind_impl(
    cls: type[EnumNodeType], node_type: EnumNodeType
) -> EnumNodeKind:
    """
    Get the architectural kind for this node type.

    Args:
        node_type: The specific node type to classify

    Returns:
        The architectural kind (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR, or RUNTIME_HOST)

    Raises:
        ModelOnexError: If the node type has no kind mapping (should never happen if _KIND_MAP is complete)

    Example:
        >>> EnumNodeType.get_node_kind(EnumNodeType.TRANSFORMER)
        EnumNodeKind.COMPUTE

        >>> EnumNodeType.get_node_kind(EnumNodeType.TOOL)
        EnumNodeKind.EFFECT
    """
    from omnibase_core.enums.enum_node_kind import EnumNodeKind as _EnumNodeKind

    try:
        result: _EnumNodeKind = cls._KIND_MAP[node_type]  # type: ignore[attr-defined]
        return result
    except KeyError as e:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        raise ModelOnexError(
            message=f"No kind mapping for node type '{node_type}'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "node_type": str(node_type),
                "available_types": [str(k) for k in cls._KIND_MAP.keys()],  # type: ignore[attr-defined]
            },
        ) from e


# Attach the classmethod to EnumNodeType
EnumNodeType.get_node_kind = _get_node_kind_impl  # type: ignore[attr-defined]

# Export for use
__all__ = ["EnumNodeType"]

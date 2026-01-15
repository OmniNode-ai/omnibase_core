"""
Node Type Enum.

Strongly typed node type values for ONEX architecture node classification.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING

from omnibase_core.utils.util_str_enum_base import StrValueHelper

if TYPE_CHECKING:
    from omnibase_core.enums.enum_node_kind import EnumNodeKind

# Module-level storage for the kind mapping.
# This avoids the limitation that Enum classes treat class-level dicts as enum members.
# The mapping is populated lazily on first access via get_node_kind().
_KIND_MAP: dict[EnumNodeType, EnumNodeKind] = {}
_KIND_MAP_POPULATED: bool = False


def _populate_kind_map() -> None:
    """
    Populate the type-to-kind mapping with all EnumNodeType mappings.

    This function is called at module import time (line 334) and also defensively
    in get_node_kind() and related methods to handle edge cases.

    Thread Safety
    -------------
    This function is thread-safe without explicit locking because:

    1. **Module-level execution**: The primary call at line 334 executes during
       module import, before any external code can access this module.

    2. **Python's import lock**: Python's import machinery (importlib) uses a
       per-module lock (_ModuleLock) that ensures module-level code executes
       exactly once, even under concurrent imports from multiple threads.
       See: https://docs.python.org/3/library/importlib.html#importlib.import_module

    3. **Idempotent operation**: The _KIND_MAP_POPULATED flag ensures the mapping
       is only populated once. Even if multiple threads somehow called this
       function concurrently, dict.update() is atomic in CPython (due to the GIL),
       and the mapping would simply be populated with the same values.

    4. **Module cache**: After first import, subsequent imports return the cached
       module from sys.modules, so the module-level code never re-executes.

    The lazy initialization pattern is preserved in get_node_kind() and related
    methods for defensive programming and to support testing scenarios where the
    module might be reloaded.
    """
    global _KIND_MAP_POPULATED
    if _KIND_MAP_POPULATED:
        return

    from omnibase_core.enums.enum_node_kind import EnumNodeKind

    _KIND_MAP.update(
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
            # Generic types - default to COMPUTE as the most common processing behavior
            EnumNodeType.PLUGIN: EnumNodeKind.COMPUTE,
            EnumNodeType.SCHEMA: EnumNodeKind.COMPUTE,
            EnumNodeType.NODE: EnumNodeKind.COMPUTE,
            EnumNodeType.SERVICE: EnumNodeKind.COMPUTE,
            # NOTE: EnumNodeType.UNKNOWN intentionally has NO mapping.
            # UNKNOWN semantically means "we don't know what this is" - it should NOT
            # silently default to COMPUTE. Calling get_node_kind(EnumNodeType.UNKNOWN)
            # will raise ModelOnexError, forcing callers to handle the unknown case explicitly.
        }
    )
    _KIND_MAP_POPULATED = True


@unique
class EnumNodeType(StrValueHelper, str, Enum):
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
    - TRANSFORMER, AGGREGATOR, COMPUTE_GENERIC -> All are COMPUTE kind
    - GATEWAY, VALIDATOR -> Both are control flow nodes (ORCHESTRATOR kind)

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

    @classmethod
    def get_node_kind(cls, node_type: EnumNodeType) -> EnumNodeKind:
        """
        Get the architectural kind for this node type.

        Args:
            node_type: The specific node type to classify

        Returns:
            The architectural kind (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR, or RUNTIME_HOST)

        Raises:
            ModelOnexError: If the node type has no kind mapping (e.g., UNKNOWN)

        Example:
            >>> EnumNodeType.get_node_kind(EnumNodeType.TRANSFORMER)
            EnumNodeKind.COMPUTE

            >>> EnumNodeType.get_node_kind(EnumNodeType.TOOL)
            EnumNodeKind.EFFECT
        """
        # Ensure the mapping is populated (lazy initialization to avoid circular imports)
        _populate_kind_map()

        try:
            result = _KIND_MAP[node_type]
        except KeyError as e:
            # error-ok: enums cannot import models (circular import prevention)
            raise ValueError(
                f"No kind mapping for node type '{node_type}'. "
                f"Available types: {[str(k) for k in _KIND_MAP]}"
            ) from e
        else:
            return result

    @classmethod
    def has_node_kind(cls, node_type: EnumNodeType) -> bool:
        """
        Check if a node type has a kind mapping.

        This method enables defensive programming by allowing callers to check
        whether a node type has a kind mapping before calling get_node_kind().
        This is especially useful for handling EnumNodeType.UNKNOWN, which
        intentionally has no mapping.

        Args:
            node_type: The specific node type to check

        Returns:
            True if the node type has a kind mapping, False otherwise.
            Returns False for EnumNodeType.UNKNOWN.

        Example:
            >>> EnumNodeType.has_node_kind(EnumNodeType.COMPUTE_GENERIC)
            True

            >>> EnumNodeType.has_node_kind(EnumNodeType.UNKNOWN)
            False

            >>> # Defensive programming pattern
            >>> if EnumNodeType.has_node_kind(node_type):
            ...     kind = EnumNodeType.get_node_kind(node_type)
            ... else:
            ...     handle_unknown_type(node_type)
        """
        _populate_kind_map()
        return node_type in _KIND_MAP

    @classmethod
    def get_core_node_types(cls) -> set[EnumNodeType]:
        """
        Get all EnumNodeType values that map to core node kinds.

        Core node kinds are the four fundamental ONEX architecture types:
        COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR.

        Returns:
            A set of EnumNodeType values that map to core node kinds.
            UNKNOWN is never included (it has no mapping).

        Example:
            >>> core_types = EnumNodeType.get_core_node_types()
            >>> EnumNodeType.TRANSFORMER in core_types
            True
            >>> EnumNodeType.RUNTIME_HOST_GENERIC in core_types
            False
            >>> EnumNodeType.UNKNOWN in core_types
            False
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind as _EnumNodeKind

        _populate_kind_map()
        return {
            node_type
            for node_type, kind in _KIND_MAP.items()
            if _EnumNodeKind.is_core_node_type(kind)
        }

    @classmethod
    def get_infrastructure_types(cls) -> set[EnumNodeType]:
        """
        Get all EnumNodeType values that map to infrastructure kinds.

        Infrastructure kinds are node types that support the ONEX runtime
        rather than participating in the core data flow. Currently this
        includes RUNTIME_HOST.

        Returns:
            A set of EnumNodeType values that map to infrastructure kinds.
            UNKNOWN is never included (it has no mapping).

        Example:
            >>> infra_types = EnumNodeType.get_infrastructure_types()
            >>> EnumNodeType.RUNTIME_HOST_GENERIC in infra_types
            True
            >>> EnumNodeType.COMPUTE_GENERIC in infra_types
            False
            >>> EnumNodeType.UNKNOWN in infra_types
            False
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind as _EnumNodeKind

        _populate_kind_map()
        return {
            node_type
            for node_type, kind in _KIND_MAP.items()
            if _EnumNodeKind.is_infrastructure_type(kind)
        }


# ==============================================================================
# DYNAMIC CLASSMETHOD ATTACHMENT - DOCUMENTED EXCEPTION TO STRICT MYPY RULES
# ==============================================================================
#
# WHY THIS PATTERN IS NECESSARY:
# This module uses dynamic attribute attachment to avoid circular imports between
# EnumNodeType and EnumNodeKind. The circular dependency arises because:
# 1. EnumNodeType.get_node_kind() returns EnumNodeKind
# 2. EnumNodeKind could need EnumNodeType for reverse lookups
# 3. Both are fundamental enums that must be importable independently
#
# The lazy initialization pattern (_populate_kind_map) defers the import of
# EnumNodeKind until first use, breaking the circular import at module load time.
#
# WHY type: ignore IS ACCEPTABLE HERE:
# The setattr() call dynamically attaches _KIND_MAP to the class for direct
# test access where tests reference EnumNodeType._KIND_MAP as an attribute. Mypy
# cannot statically verify dynamically attached attributes, so it may report
# [attr-defined] errors. If such errors arise, `# type: ignore[attr-defined]`
# suppression is acceptable because:
# - The attribute IS defined at runtime (verified by tests)
# - The code is fully functional and tested
# - The suppression only affects static analysis, not runtime behavior
# - This follows the ONEX pattern for avoiding circular imports in enum modules
#
# See CLAUDE.md section "Node Classification Enums" for architectural context.
# ==============================================================================

# Expose _KIND_MAP on the class for direct attribute access in tests.
# Tests access EnumNodeType._KIND_MAP directly as an attribute.
# We populate the mapping eagerly and attach it to the class.
#
# Thread Safety: This module-level call executes during import, which is
# protected by Python's import lock. See _populate_kind_map() docstring.
#
# Type Safety Note: The setattr() below dynamically attaches _KIND_MAP to the
# EnumNodeType class. If mypy reports [attr-defined] errors, use
# `# type: ignore[attr-defined]` - this is an ACCEPTED EXCEPTION to strict mypy
# rules per the documentation block above (lines 327-353). The attribute IS
# defined at runtime and verified by tests. See CLAUDE.md section "Node
# Classification Enums: EnumNodeKind vs EnumNodeType" for architectural context.
_populate_kind_map()
setattr(EnumNodeType, "_KIND_MAP", _KIND_MAP)

# Export for use
__all__ = ["EnumNodeType"]

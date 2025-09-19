"""
Node type classification enum for ONEX 4-node architecture.

Defines the canonical node types used throughout the ONEX ecosystem
for classification and routing purposes.
"""

from enum import Enum


class EnumNodeType(str, Enum):
    """Node types following ONEX 4-node architecture."""

    # Core ONEX 4-node architecture types
    EFFECT = "effect"
    COMPUTE = "compute"
    REDUCER = "reducer"
    ORCHESTRATOR = "orchestrator"

    # Supporting node types
    REGISTRY = "registry"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    OUTPUT = "output"
    UTILITY = "utility"
    CUSTOM = "custom"

    # Legacy/compatibility types
    UNKNOWN = "unknown"
    DEPRECATED = "deprecated"

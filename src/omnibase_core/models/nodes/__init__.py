"""
Node Management Models

Models for node definitions, capabilities, configurations, and information.

NOTE: Node metadata models have been moved to omnibase_core.models.node_metadata.
Import them from there instead.
"""

from omnibase_core.models.core.model_node_info import ModelNodeInfo

__all__ = [
    "ModelNodeInfo",
]

# NOTE: model_rebuild() calls removed - Pydantic v2 handles forward references automatically
# The explicit rebuilds at module level caused import failures for forward references
# Pydantic will rebuild models lazily when first accessed

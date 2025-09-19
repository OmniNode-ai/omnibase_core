"""
Node Type Model

Modern standards module for node type models.

This module maintains compatibility while redirecting to the new enhanced model:
- ModelNodeType -> model_node_type_individual.py (enhanced with strongly typed enums)

All functionality is preserved through re-exports with enhanced type safety.
"""

# Re-export enhanced model with strongly typed enums
from .model_node_type_individual import ModelNodeType

__all__ = [
    "ModelNodeType",
]

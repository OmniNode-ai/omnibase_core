"""
ONEX Mixin Module

Provides reusable mixin classes for ONEX node patterns.
Mixins follow the single responsibility principle and provide specific capabilities
that can be composed into concrete node implementations.
"""

# Core mixins
from .mixin_node_id_from_contract import MixinNodeIdFromContract
from .mixin_node_service import MixinNodeService

__all__ = [
    "MixinNodeIdFromContract",
    "MixinNodeService",
]

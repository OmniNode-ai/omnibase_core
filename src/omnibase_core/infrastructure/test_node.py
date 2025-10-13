from __future__ import annotations

"""
Test node implementation for architecture validation.

This is a minimal test node used by the NodeArchitectureValidator
to test NodeCoreBase functionality.
"""


from typing import Any

from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class TestNode(NodeCoreBase):
    """Test node implementation for validation."""

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize test node with container."""
        super().__init__(container)

    async def process(self, input_data: Any) -> dict[str, str]:
        """Process input data for testing."""
        return {"test": "success"}


# Export for use
__all__ = [
    "TestNode",
]

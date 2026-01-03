"""
ModelWorkflowFactory

Workflow factory for LlamaIndex integration.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelWorkflowFactory:
    """Workflow factory for LlamaIndex integration."""

    def create_workflow(
        self,
        workflow_type: str,
        config: SerializedDict | None = None,
    ) -> object:
        """Create workflow instance by type."""
        config = config or {}
        # This would be expanded with actual workflow types from LlamaIndex integration
        # Return placeholder object until actual workflow types are implemented
        return None

    def list_available_workflows(self) -> list[str]:
        """List available workflow types."""
        return [
            "simple_sequential",
            "parallel_execution",
            "conditional_branching",
            "retry_with_backoff",
            "data_pipeline",
        ]

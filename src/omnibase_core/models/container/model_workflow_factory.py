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

from typing import Any

from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Workflow factory config parameter accepts dict[str, Any] for "
    "flexible workflow-specific configuration options."
)
class ModelWorkflowFactory:
    """Workflow factory for LlamaIndex integration."""

    def create_workflow(
        self,
        workflow_type: str,
        config: dict[str, Any] | None = None,
    ) -> Any:
        """Create workflow instance by type."""
        config = config or {}
        # This would be expanded with actual workflow types from LlamaIndex integration

    def list_available_workflows(self) -> list[str]:
        """List available workflow types."""
        return [
            "simple_sequential",
            "parallel_execution",
            "conditional_branching",
            "retry_with_backoff",
            "data_pipeline",
        ]

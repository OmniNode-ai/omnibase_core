"""
Orchestrator node operation data for workflow coordination.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_node_type import EnumNodeType

from .model_operation_data_base import ModelOperationDataBase


class ModelOrchestratorOperationData(ModelOperationDataBase):
    """Orchestrator node operation data for workflow coordination."""

    operation_type: Literal[EnumNodeType.ORCHESTRATOR_GENERIC] = Field(
        default=EnumNodeType.ORCHESTRATOR_GENERIC,
        description="Orchestrator operation type",
    )
    workflow_definition: str = Field(
        default=..., description="Workflow definition identifier"
    )
    coordination_strategy: str = Field(default=..., description="Coordination strategy")
    dependency_resolution: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Dependency resolution configuration",
    )
    error_handling_strategy: str = Field(
        default="stop_on_error",
        description="Error handling strategy",
    )


__all__ = ["ModelOrchestratorOperationData"]

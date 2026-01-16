from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import Field

"\nOrchestrator graph model.\n"
from pydantic import BaseModel

if TYPE_CHECKING:
    from omnibase_core.models.graph import ModelGraphEdge, ModelGraphNode


class ModelOrchestratorGraph(BaseModel):
    """ONEX graph model for orchestrator."""

    graph_id: UUID = Field(default=..., description="Graph identifier")
    graph_name: str = Field(default=..., description="Graph name")
    nodes: list[ModelGraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[ModelGraphEdge] = Field(default_factory=list, description="Graph edges")


__all__ = ["ModelOrchestratorGraph"]

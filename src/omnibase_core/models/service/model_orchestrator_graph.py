from typing import Any
from uuid import UUID

from pydantic import Field

"\nOrchestrator graph model.\n"
from pydantic import BaseModel

from .model_graph_edge import ModelGraphEdge
from .model_graph_node import ModelGraphNode


class ModelOrchestratorGraph(BaseModel):
    """ONEX graph model for orchestrator."""

    graph_id: UUID = Field(default=..., description="Graph identifier")
    graph_name: str = Field(default=..., description="Graph name")
    nodes: list[ModelGraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[ModelGraphEdge] = Field(default_factory=list, description="Graph edges")

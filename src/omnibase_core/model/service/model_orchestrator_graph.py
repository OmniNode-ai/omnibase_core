"""
Orchestrator graph model.
"""

from pydantic import BaseModel, Field

from .model_graph_edge import ModelGraphEdge
from .model_graph_node import ModelGraphNode


class ModelOrchestratorGraph(BaseModel):
    """ONEX graph model for orchestrator."""

    # Graph identification
    graph_id: str = Field(..., description="Graph identifier")
    graph_name: str = Field(..., description="Graph name")

    # Graph structure
    nodes: list[ModelGraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[ModelGraphEdge] = Field(default_factory=list, description="Graph edges")

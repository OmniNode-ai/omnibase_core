"""
Orchestrator graph model.
"""

from typing import List

from pydantic import BaseModel, Field

from .model_graph_edge import ModelGraphEdge
from .model_graph_node import ModelGraphNode


class ModelOrchestratorGraph(BaseModel):
    """ONEX graph model for orchestrator."""

    # Graph identification
    graph_id: str = Field(..., description="Graph identifier")
    graph_name: str = Field(..., description="Graph name")

    # Graph structure
    nodes: List[ModelGraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[ModelGraphEdge] = Field(default_factory=list, description="Graph edges")

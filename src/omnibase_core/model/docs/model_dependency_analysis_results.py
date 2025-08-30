"""
Dependency Analysis Results Model

Results of dependency analysis.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.docs.model_dependency_edge import ModelDependencyEdge
from omnibase_core.model.docs.model_dependency_node import ModelDependencyNode


class ModelDependencyAnalysisResults(BaseModel):
    """Results of dependency analysis."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    nodes: List[ModelDependencyNode] = Field(
        description="Nodes in the dependency graph"
    )
    edges: List[ModelDependencyEdge] = Field(
        description="Edges in the dependency graph"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the analysis was performed"
    )

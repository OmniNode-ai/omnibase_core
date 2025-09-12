"""
Dependency Analysis Results Model

Results of dependency analysis.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.docs.model_dependency_edge import ModelDependencyEdge
from omnibase_core.models.docs.model_dependency_node import ModelDependencyNode


class ModelDependencyAnalysisResults(BaseModel):
    """Results of dependency analysis."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    nodes: list[ModelDependencyNode] = Field(
        description="Nodes in the dependency graph",
    )
    edges: list[ModelDependencyEdge] = Field(
        description="Edges in the dependency graph",
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the analysis was performed",
    )

"""
Entity centrality model for graph analysis metrics.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEntityCentrality(BaseModel):
    """Model for entity centrality scores and graph analysis metrics."""

    entity_id: str = Field(..., description="Entity identifier")
    degree_centrality: float = Field(..., description="Degree centrality score")
    betweenness_centrality: float = Field(
        ...,
        description="Betweenness centrality score",
    )
    closeness_centrality: float = Field(..., description="Closeness centrality score")
    eigenvector_centrality: float = Field(
        ...,
        description="Eigenvector centrality score",
    )
    pagerank_score: float = Field(..., description="PageRank score")
    overall_importance: float = Field(..., description="Combined importance score")

    model_config = ConfigDict(frozen=True, validate_assignment=True)

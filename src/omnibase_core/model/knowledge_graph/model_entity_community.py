"""
Entity community model for semantic clustering results.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEntityCommunity(BaseModel):
    """Model for entity communities/clusters in knowledge graph."""

    community_id: str = Field(..., description="Unique community identifier")
    community_name: str = Field(..., description="Descriptive name for the community")
    entity_ids: list[str] = Field(
        ...,
        description="List of entity IDs in this community",
    )
    coherence_score: float = Field(
        ...,
        description="Semantic coherence within community (0.0-1.0)",
    )
    size: int = Field(..., description="Number of entities in community")
    density: float = Field(..., description="Connection density within community")
    central_entity_id: str = Field(..., description="Most central entity in community")
    dominant_themes: list[str] = Field(
        default_factory=list,
        description="Main themes/topics in community",
    )

    model_config = ConfigDict(frozen=True, validate_assignment=True)

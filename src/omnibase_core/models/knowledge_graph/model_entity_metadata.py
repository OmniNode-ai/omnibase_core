"""
Entity metadata model for additional structured information.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.knowledge_graph.model_code_location import ModelCodeLocation
from omnibase_core.models.knowledge_graph.model_documentation_reference import (
    ModelDocumentationReference,
)


class ModelEntityMetadata(BaseModel):
    """Model for entity metadata containing structured additional information."""

    # Source information
    file_hash: str = Field(..., description="Hash of source file content")
    extraction_method: str = Field(
        ...,
        description="Method used to extract this entity",
    )
    extraction_confidence: float = Field(
        ...,
        description="Confidence in extraction method",
    )

    # Code-specific metadata
    code_location: ModelCodeLocation | None = Field(
        None,
        description="Code location details",
    )

    # Documentation metadata
    documentation_refs: list[ModelDocumentationReference] = Field(
        default_factory=list,
        description="References to related documentation",
    )

    # Semantic metadata
    semantic_similarity_threshold: float = Field(
        0.8,
        description="Threshold for semantic matching",
    )
    complexity_score: float = Field(0.0, description="Complexity assessment (0.0-1.0)")
    importance_score: float = Field(0.0, description="Importance in system (0.0-1.0)")

    # Relationship metadata
    relationship_count: int = Field(
        0,
        description="Number of relationships this entity has",
    )
    centrality_score: float = Field(0.0, description="Graph centrality score")

    # Quality metadata
    validation_status: str = Field("pending", description="Validation status of entity")
    review_status: str = Field("unreviewed", description="Human review status")

    model_config = ConfigDict(frozen=False, validate_assignment=True)

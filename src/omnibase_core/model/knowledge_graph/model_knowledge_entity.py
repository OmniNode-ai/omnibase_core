"""
Knowledge entity model for semantic graph representation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.knowledge_graph.model_entity_metadata import (
    ModelEntityMetadata,
)
from omnibase_core.model.knowledge_graph.model_entity_type import ModelEntityType


class ModelKnowledgeEntity(BaseModel):
    """Model for semantic entities in the knowledge graph."""

    entity_id: str = Field(..., description="Unique identifier for the entity")
    name: str = Field(..., description="Human-readable name of the entity")
    entity_type: ModelEntityType = Field(
        ...,
        description="Type classification of the entity",
    )
    description: str = Field(..., description="Detailed description of the entity")
    source_path: str = Field(..., description="File path where entity was discovered")
    confidence_score: float = Field(
        ...,
        description="Confidence in entity extraction (0.0-1.0)",
    )
    metadata: ModelEntityMetadata = Field(
        ...,
        description="Additional structured metadata",
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for the entity",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Semantic tags for categorization",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )
    source_line_number: int | None = Field(
        None,
        description="Line number in source file",
    )
    documentation_coverage: float = Field(
        0.0,
        description="Coverage score for documentation (0.0-1.0)",
    )

    model_config = ConfigDict(frozen=False, validate_assignment=True)

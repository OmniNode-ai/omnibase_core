"""
Knowledge relationship model for semantic connections between entities.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.knowledge_graph.model_relationship_evidence import \
    ModelRelationshipEvidence
from omnibase_core.model.knowledge_graph.model_relationship_type import \
    ModelRelationshipType


class ModelKnowledgeRelationship(BaseModel):
    """Model for semantic relationships between knowledge entities."""

    relationship_id: str = Field(
        ..., description="Unique identifier for the relationship"
    )
    source_entity_id: str = Field(..., description="ID of the source entity")
    target_entity_id: str = Field(..., description="ID of the target entity")
    relationship_type: ModelRelationshipType = Field(
        ..., description="Type and properties of relationship"
    )
    confidence_score: float = Field(
        ..., description="Confidence in relationship accuracy (0.0-1.0)"
    )
    weight: float = Field(1.0, description="Strength/importance of the relationship")

    # Evidence and validation
    evidence: List[ModelRelationshipEvidence] = Field(
        default_factory=list, description="Evidence supporting this relationship"
    )

    # Bidirectional properties
    is_bidirectional: bool = Field(
        False, description="Whether relationship works in both directions"
    )
    reverse_relationship_type: Optional[str] = Field(
        None, description="Type when traversed in reverse"
    )

    # Temporal aspects
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    valid_from: Optional[datetime] = Field(
        None, description="When relationship became valid"
    )
    valid_until: Optional[datetime] = Field(
        None, description="When relationship expires"
    )

    # Metadata
    detection_method: str = Field(
        ..., description="Method used to detect this relationship"
    )
    validation_status: str = Field("unvalidated", description="Human validation status")
    tags: List[str] = Field(
        default_factory=list, description="Semantic tags for categorization"
    )

    model_config = ConfigDict(frozen=False, validate_assignment=True)

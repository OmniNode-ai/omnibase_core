"""
Semantic boundary model for LangExtract-enhanced adaptive chunking.

Represents a detected semantic boundary in text content with confidence scoring.
"""

from pydantic import BaseModel, Field


class ModelModelSemanticBoundaryMetadata(BaseModel):
    """Metadata for semantic boundary detection."""

    text_value: str | None = Field(None, description="Text metadata value")
    numeric_value: float | None = Field(None, description="Numeric metadata value")
    boolean_value: bool | None = Field(None, description="Boolean metadata value")
    pattern: str | None = Field(
        None,
        description="Pattern name associated with boundary",
    )
    severity: str | None = Field(None, description="Severity level of the boundary")
    entity_name: str | None = Field(
        None,
        description="Entity name if boundary is entity-related",
    )
    entity_type: str | None = Field(
        None,
        description="Entity type if boundary is entity-related",
    )
    type: str | None = Field(
        None,
        description="Type classification for structural boundaries",
    )


class ModelModelSemanticBoundary(BaseModel):
    """Represents a semantic boundary detected in text content."""

    position: int = Field(
        ...,
        description="Character position of the boundary in the text",
    )
    boundary_type: str = Field(
        ...,
        description="Type of boundary: function, class, entity, pattern, structural",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this boundary detection",
    )
    reason: str = Field(
        ...,
        description="Explanation for why this boundary was detected",
    )
    metadata: ModelModelSemanticBoundaryMetadata = Field(
        default_factory=ModelModelSemanticBoundaryMetadata,
        description="Additional metadata about the boundary",
    )

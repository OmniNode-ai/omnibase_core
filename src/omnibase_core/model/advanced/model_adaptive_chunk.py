"""
Adaptive chunk model for LangExtract-enhanced chunking.

Represents a single chunk created by the adaptive chunking process.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelModelAdaptiveChunkMetadata(BaseModel):
    """Metadata for adaptively generated chunks."""

    density_score: float = Field(
        ..., ge=0.0, le=1.0, description="Average content density for this chunk"
    )
    adaptive_size: int = Field(
        ..., description="Calculated adaptive size for this chunk"
    )
    preserved_entities: List[str] = Field(
        default_factory=list, description="Names of entities preserved in this chunk"
    )
    boundary_type: str = Field(
        ..., description="Type of boundary used to create this chunk"
    )
    boundary_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the boundary selection"
    )
    langextract_patterns_detected: List[str] = Field(
        default_factory=list, description="LangExtract patterns detected in this chunk"
    )
    intelligence_enhanced: bool = Field(
        default=False, description="Whether this chunk used LangExtract intelligence"
    )


class ModelModelAdaptiveChunk(BaseModel):
    """Represents a single adaptive chunk with metadata."""

    passage_id: str = Field(..., description="Unique identifier for this chunk")
    start_char: str = Field(
        ..., description="Starting character position in original content"
    )
    end_char: str = Field(
        ..., description="Ending character position in original content"
    )
    content: str = Field(..., description="The actual text content of this chunk")
    adaptive_metadata: ModelModelAdaptiveChunkMetadata = Field(
        ..., description="Adaptive chunking metadata for this chunk"
    )

"""Document metadata model with strong typing."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelDocumentMetadata(BaseModel):
    """Strongly typed document metadata model."""

    document_id: str = Field(min_length=1, description="Unique document identifier")
    content: str = Field(description="Document content text")

    # Core metadata
    title: Optional[str] = Field(default=None, description="Document title")
    source: Optional[str] = Field(default=None, description="Document source or origin")
    file_type: Optional[str] = Field(default=None, description="File type or format")

    # Semantic metadata
    embedding_model: Optional[str] = Field(
        default=None, description="Embedding model used"
    )
    chunk_index: Optional[int] = Field(
        default=None, ge=0, description="Chunk index within document"
    )
    parent_document_id: Optional[str] = Field(
        default=None, description="Parent document ID for chunks"
    )

    # Search metadata
    score: Optional[float] = Field(
        default=None, description="Relevance score from search"
    )
    retrieval_method: Optional[str] = Field(
        default=None, description="Method used for retrieval"
    )

    # Processing metadata
    created_at: Optional[datetime] = Field(
        default=None, description="Document creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Document update timestamp"
    )
    processed_at: Optional[datetime] = Field(
        default=None, description="Document processing timestamp"
    )

    # Quality metadata
    quality_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Document quality score"
    )
    language: Optional[str] = Field(
        default=None, description="Detected document language"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

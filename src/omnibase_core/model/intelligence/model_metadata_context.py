"""
Metadata context model for intelligence system.
"""

from pydantic import BaseModel, Field


class ModelMetadataContext(BaseModel):
    """Metadata context for intelligent processing."""

    file_path: str = Field(..., description="Path to file being processed")
    content_type: str = Field(..., description="Type of content")
    processing_timestamp: str = Field(..., description="When processing occurred")
    metadata: str | None = Field(
        None,
        description="Additional metadata as JSON string",
    )

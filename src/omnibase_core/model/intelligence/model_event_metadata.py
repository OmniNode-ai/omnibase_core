"""
Event metadata model - Strongly typed event metadata structure.

Replaces Dict[str, Any] usage with strongly typed event metadata information.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelEventMetadata(BaseModel):
    """Strongly typed event metadata."""

    schema_version: str = Field(default="1.0.0", description="Event schema version")
    routing_hints: List[str] = Field(
        default_factory=list, description="Routing optimization hints"
    )
    processing_hints: List[str] = Field(
        default_factory=list, description="Processing optimization hints"
    )
    retention_policy: Optional[str] = Field(
        default=None, description="Event retention policy"
    )
    classification: Optional[str] = Field(
        default=None, description="Event classification level"
    )
    tags: List[str] = Field(
        default_factory=list, description="Event tags for categorization"
    )
    created_by: Optional[str] = Field(
        default=None, description="Event creator identifier"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Event creation timestamp"
    )

"""
ModelPermissionMetadata: Additional metadata for permissions.

This model provides structured metadata for permissions without using Any types.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelPermissionMetadata(BaseModel):
    """Additional metadata for permissions."""

    tags: List[str] = Field(default_factory=list, description="Metadata tags")
    category: Optional[str] = Field(None, description="Permission category")
    priority: Optional[int] = Field(
        None, description="Permission priority", ge=1, le=10
    )
    source_system: Optional[str] = Field(None, description="Originating system")
    external_id: Optional[str] = Field(None, description="External system identifier")
    notes: Optional[str] = Field(None, description="Additional notes")

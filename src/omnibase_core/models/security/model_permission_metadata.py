from typing import Any

from pydantic import Field

"""
ModelPermissionMetadata: Additional metadata for permissions.

This model provides structured metadata for permissions without using Any types.
"""

from pydantic import BaseModel, Field


class ModelPermissionMetadata(BaseModel):
    """Additional metadata for permissions."""

    tags: list[str] = Field(default_factory=list, description="Metadata tags")
    category: str | None = Field(None, description="Permission category")
    priority: int | None = Field(
        None,
        description="Permission priority",
        ge=1,
        le=10,
    )
    source_system: str | None = Field(None, description="Originating system")
    external_id: str | None = Field(None, description="External system identifier")
    notes: str | None = Field(None, description="Additional notes")

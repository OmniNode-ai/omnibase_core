from uuid import UUID

from pydantic import Field

"\nModelPermissionMetadata: Additional metadata for permissions.\n\nThis model provides structured metadata for permissions without using Any types.\n"
from pydantic import BaseModel


class ModelPermissionMetadata(BaseModel):
    """Additional metadata for permissions."""

    tags: list[str] = Field(default_factory=list, description="Metadata tags")
    category: str | None = Field(default=None, description="Permission category")
    priority: int | None = Field(
        default=None, description="Permission priority", ge=1, le=10
    )
    source_system: str | None = Field(default=None, description="Originating system")
    external_id: UUID | None = Field(
        default=None, description="External system identifier"
    )
    notes: str | None = Field(default=None, description="Additional notes")

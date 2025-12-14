"""
Metadata Base Model.

Base class for all metadata models in the system,
providing common fields and functionality.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_tag import ModelTag
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelMetadataBase(BaseModel):
    """Base metadata model for all metadata types"""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )

    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Metadata version",
    )

    tags: list[ModelTag] = Field(default_factory=list, description="Metadata tags")

    def add_tag(self, tag: ModelTag) -> None:
        """Add a tag to metadata."""
        if not any(t.matches(tag) for t in self.tags):
            self.tags.append(tag)

    def remove_tag(self, tag: ModelTag) -> None:
        """Remove a tag from metadata."""
        self.tags = [t for t in self.tags if not t.matches(tag)]

    def has_tag(self, tag: ModelTag) -> bool:
        """Check if metadata has a specific tag."""
        return any(t.matches(tag) for t in self.tags)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

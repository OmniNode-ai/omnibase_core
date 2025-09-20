"""
Example metadata model with strong typing and UUID support.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_example_category import EnumExampleCategory


class ModelExampleMetadata(BaseModel):
    """
    Metadata for an example with strong typing and UUID support.

    Provides structured metadata with enum-based categorization
    and UUID-based identification for examples.
    """

    # Metadata identification
    metadata_id: UUID | None = Field(
        default=None,
        description="Unique identifier for this metadata"
    )
    name: str = Field(..., description="Example name")
    description: str | None = Field(None, description="Example description")

    # Categorization with enum
    category: EnumExampleCategory | None = Field(
        default=None,
        description="Example category using enum"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Example tags for additional categorization"
    )

    # Ownership and authorship
    author_id: UUID | None = Field(
        default=None,
        description="UUID of the example author"
    )
    author_name: str | None = Field(
        default=None,
        description="Name of the example author"
    )
    organization: str | None = Field(
        default=None,
        description="Organization or team that created the example"
    )

    # Version and lifecycle
    version: str | None = Field(
        default=None,
        description="Version of the example"
    )
    status: str | None = Field(
        default=None,
        description="Status of the example (active, deprecated, etc.)"
    )

    # Timestamps
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp"
    )
    published_at: datetime | None = Field(
        default=None,
        description="Publication timestamp"
    )

    # Usage and dependencies
    dependencies: list[str] | None = Field(
        default=None,
        description="List of dependencies for this example"
    )
    requirements: list[str] | None = Field(
        default=None,
        description="List of requirements for this example"
    )
    usage_count: int | None = Field(
        default=None,
        description="Number of times this example has been used"
    )

    # Quality metrics
    complexity_level: str | None = Field(
        default=None,
        description="Complexity level (beginner, intermediate, advanced)"
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        description="Estimated time to complete in minutes"
    )
    difficulty_rating: float | None = Field(
        default=None,
        description="Difficulty rating from 1.0 to 5.0"
    )

    # Documentation links
    documentation_url: str | None = Field(
        default=None,
        description="URL to additional documentation"
    )
    source_url: str | None = Field(
        default=None,
        description="URL to source code or origin"
    )
    tutorial_url: str | None = Field(
        default=None,
        description="URL to related tutorial"
    )

    # Helper methods
    def has_author(self) -> bool:
        """Check if the example has author information."""
        return self.author_id is not None or self.author_name is not None

    def is_beginner_friendly(self) -> bool:
        """Check if the example is beginner-friendly."""
        if self.complexity_level:
            return self.complexity_level.lower() == "beginner"
        if self.difficulty_rating:
            return self.difficulty_rating <= 2.0
        return False

    def is_advanced(self) -> bool:
        """Check if the example is advanced."""
        if self.complexity_level:
            return self.complexity_level.lower() == "advanced"
        if self.difficulty_rating:
            return self.difficulty_rating >= 4.0
        return False

    def has_documentation(self) -> bool:
        """Check if the example has documentation links."""
        return any([
            self.documentation_url,
            self.source_url,
            self.tutorial_url
        ])

    def add_tag(self, tag: str) -> None:
        """Add a tag to the example."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the example. Returns True if removed."""
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if the example has a specific tag."""
        return tag in self.tags

    def get_age_days(self) -> int | None:
        """Get the age of the example in days."""
        if self.created_at:
            return (datetime.utcnow() - self.created_at).days
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelExampleMetadata":
        """Create from dictionary with validation."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data)}")

        return cls(**data)

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str | None = None,
        category: EnumExampleCategory | None = None,
        author_name: str | None = None
    ) -> "ModelExampleMetadata":
        """Create simple metadata with basic information."""
        return cls(
            name=name,
            description=description,
            category=category,
            author_name=author_name,
            created_at=datetime.utcnow()
        )
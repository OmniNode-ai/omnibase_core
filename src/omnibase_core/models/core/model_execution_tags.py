"""
Execution Tags Model

Model for managing execution tags with validation and categorization.
"""

from typing import Dict, List

from pydantic import BaseModel, Field, field_validator


class ModelTag(BaseModel):
    """Model for individual execution tags."""

    key: str = Field(..., description="Tag key")
    value: str = Field(..., description="Tag value")
    category: str = Field(default="general", description="Tag category")
    source: str = Field(default="user", description="Source of the tag")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate tag key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Tag key cannot be empty")
        if len(v) > 64:
            raise ValueError("Tag key must be 64 characters or less")
        # Allow alphanumeric, hyphens, underscores, and dots
        import re

        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Tag key contains invalid characters")
        return v.strip()

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Validate tag value format."""
        if len(v) > 256:
            raise ValueError("Tag value must be 256 characters or less")
        return v.strip()


class ModelExecutionTags(BaseModel):
    """Model for execution tag management."""

    tags: List[ModelTag] = Field(
        default_factory=list, description="List of execution tags"
    )

    def add_tag(
        self, key: str, value: str, category: str = "general", source: str = "user"
    ) -> None:
        """Add a tag to the collection."""
        # Remove existing tag with same key if present
        self.remove_tag(key)

        tag = ModelTag(key=key, value=value, category=category, source=source)
        self.tags.append(tag)

    def remove_tag(self, key: str) -> bool:
        """Remove a tag by key. Returns True if tag was found and removed."""
        original_len = len(self.tags)
        self.tags = [tag for tag in self.tags if tag.key != key]
        return len(self.tags) < original_len

    def get_tag_value(self, key: str) -> str | None:
        """Get the value of a tag by key."""
        for tag in self.tags:
            if tag.key == key:
                return tag.value
        return None

    def has_tag(self, key: str) -> bool:
        """Check if a tag with the given key exists."""
        return any(tag.key == key for tag in self.tags)

    def get_tags_by_category(self, category: str) -> List[ModelTag]:
        """Get all tags by category."""
        return [tag for tag in self.tags if tag.category == category]

    def get_tags_by_source(self, source: str) -> List[ModelTag]:
        """Get all tags by source."""
        return [tag for tag in self.tags if tag.source == source]

    def to_dict(self) -> Dict[str, str]:
        """Convert to simple key-value dictionary (legacy compatibility)."""
        return {tag.key: tag.value for tag in self.tags}

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        return list(set(tag.category for tag in self.tags))

    def get_sources(self) -> List[str]:
        """Get list of unique sources."""
        return list(set(tag.source for tag in self.tags))

    @classmethod
    def from_dict(cls, tag_dict: Dict[str, str]) -> "ModelExecutionTags":
        """Create instance from simple dictionary (legacy compatibility)."""
        instance = cls()
        for key, value in tag_dict.items():
            instance.add_tag(key, value)
        return instance

    def get_tag_count(self) -> int:
        """Get total number of tags."""
        return len(self.tags)

    def clear(self) -> None:
        """Remove all tags."""
        self.tags.clear()

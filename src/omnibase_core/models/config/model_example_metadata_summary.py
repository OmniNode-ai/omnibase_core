"""
Example metadata summary model.

This module provides the ModelExampleMetadataSummary class for clean
metadata summary following ONEX naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from ..metadata.model_semver import ModelSemVer


class ModelExampleMetadataSummary(BaseModel):
    """Clean model for metadata summary."""

    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Update timestamp")
    version: ModelSemVer | None = Field(None, description="Metadata version")
    author_id: UUID | None = Field(None, description="UUID of the author")
    author_display_name: str | None = Field(None, description="Human-readable author name")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    custom_fields: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Custom metadata fields with basic types only"
    )

    @property
    def author(self) -> str | None:
        """Backward compatibility property for author."""
        return self.author_display_name

    @author.setter
    def author(self, value: str | None) -> None:
        """Backward compatibility setter for author."""
        self.author_display_name = value

    @classmethod
    def create_with_legacy_author(
        cls,
        author_name: str,
        created_at: str | None = None,
        updated_at: str | None = None,
        version: ModelSemVer | None = None,
        tags: list[str] | None = None,
        custom_fields: dict[str, str | int | bool | float] | None = None,
    ) -> ModelExampleMetadataSummary:
        """Factory method to create metadata summary with legacy author name."""
        import hashlib

        # Generate UUID for author
        author_hash = hashlib.sha256(author_name.encode()).hexdigest()
        author_id = UUID(f"{author_hash[:8]}-{author_hash[8:12]}-{author_hash[12:16]}-{author_hash[16:20]}-{author_hash[20:32]}")

        return cls(
            created_at=created_at,
            updated_at=updated_at,
            version=version,
            author_id=author_id,
            author_display_name=author_name,
            tags=tags or [],
            custom_fields=custom_fields or {},
        )

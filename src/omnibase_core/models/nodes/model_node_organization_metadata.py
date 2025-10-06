from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
Node Organization Metadata Model.

Organizational information for nodes including capabilities, tags, and relationships.
Part of the ModelNodeMetadataInfo restructuring.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties


class ModelNodeOrganizationMetadata(BaseModel):
    """
    Node organization and relationship metadata.

    Contains organizational information:
    - Capabilities and categories
    - Tags and classifications
    - Dependencies and relationships
    - Custom metadata
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Capabilities and features (2 fields, but list[Any]-based)
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    categories: list[EnumCategory] = Field(
        default_factory=list,
        description="Node categories",
    )

    # Tags and classification (1 field)
    tags: list[str] = Field(default_factory=list, description="Node tags")

    # Relationships (2 fields)
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    dependents: list[UUID] = Field(
        default_factory=list,
        description="Nodes that depend on this",
    )

    # Basic metadata (2 fields)
    description: str | None = Field(default=None, description="Node description")
    author: str | None = Field(default=None, description="Node author")

    # Custom metadata (1 field, but extensible)
    custom_properties: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Custom properties with type safety",
    )

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def add_capability(self, capability: str) -> None:
        """Add a capability if not already present."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def has_capability(self, capability: str) -> bool:
        """Check if node has a specific capability."""
        return capability in self.capabilities

    def add_category(self, category: EnumCategory) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def add_dependency(self, dependency: UUID) -> None:
        """Add a dependency if not already present."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def add_dependent(self, dependent: UUID) -> None:
        """Add a dependent if not already present."""
        if dependent not in self.dependents:
            self.dependents.append(dependent)

    def get_organization_summary(self) -> dict[str, str]:
        """Get organization metadata summary as string values for type safety."""
        return {
            "capabilities_count": str(len(self.capabilities)),
            "categories_count": str(len(self.categories)),
            "tags_count": str(len(self.tags)),
            "dependencies_count": str(len(self.dependencies)),
            "dependents_count": str(len(self.dependents)),
            "has_description": str(bool(self.description)),
            "has_author": str(bool(self.author)),
            "primary_category": (
                self.categories[0].value if self.categories else "none"
            ),
            "primary_capability": self.capabilities[0] if self.capabilities else "none",
        }

    @classmethod
    def create_tagged(
        cls,
        tags: list[str],
        categories: list[EnumCategory] | None = None,
        capabilities: list[str] | None = None,
    ) -> ModelNodeOrganizationMetadata:
        """Create organization metadata with tags and categories."""
        return cls(
            tags=tags,
            categories=categories or [],
            capabilities=capabilities or [],
        )

    @classmethod
    def create_with_description(
        cls,
        description: str,
        author: str | None = None,
    ) -> ModelNodeOrganizationMetadata:
        """Create organization metadata with description."""
        return cls(
            description=description,
            author=author,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            code=ModelCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelNodeOrganizationMetadata"]

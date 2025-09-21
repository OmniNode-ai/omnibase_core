"""
Node Organization Metadata Model.

Organizational information for nodes including capabilities, tags, and relationships.
Part of the ModelNodeMetadataInfo restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..core.model_custom_properties import ModelCustomProperties


class ModelNodeOrganizationMetadata(BaseModel):
    """
    Node organization and relationship metadata.

    Contains organizational information:
    - Capabilities and categories
    - Tags and classifications
    - Dependencies and relationships
    - Custom metadata
    """

    # Capabilities and features (2 fields, but list-based)
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    categories: list[str] = Field(default_factory=list, description="Node categories")

    # Tags and classification (1 field)
    tags: list[str] = Field(default_factory=list, description="Node tags")

    # Relationships (2 fields)
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    dependents: list[str] = Field(
        default_factory=list,
        description="Nodes that depend on this",
    )

    # Basic metadata (2 fields)
    description: str | None = Field(default=None, description="Node description")
    author: str | None = Field(default=None, description="Node author")

    # Custom metadata (1 field, but extensible)
    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
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

    def add_category(self, category: str) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency if not already present."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def add_dependent(self, dependent: str) -> None:
        """Add a dependent if not already present."""
        if dependent not in self.dependents:
            self.dependents.append(dependent)

    def get_organization_summary(self) -> dict[str, list[str] | int | str | None]:
        """Get organization metadata summary."""
        return {
            "capabilities_count": len(self.capabilities),
            "categories_count": len(self.categories),
            "tags_count": len(self.tags),
            "dependencies_count": len(self.dependencies),
            "dependents_count": len(self.dependents),
            "has_description": bool(self.description),
            "has_author": bool(self.author),
            "primary_category": self.categories[0] if self.categories else None,
            "primary_capability": self.capabilities[0] if self.capabilities else None,
        }

    @classmethod
    def create_tagged(
        cls,
        tags: list[str],
        categories: list[str] | None = None,
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


# Export for use
__all__ = ["ModelNodeOrganizationMetadata"]
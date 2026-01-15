"""
Node Categorization Model.

Categories, tags, and relationship tracking for nodes.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.type_json import JsonType


class ModelNodeCategorization(BaseModel):
    """
    Node categorization with tags, categories, and relationships.

    Focused on organizational and relational aspects of nodes.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Categories and organization
    tags: list[str] = Field(default_factory=list, description="Node tags")
    categories: list[str] = Field(default_factory=list, description="Node categories")
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    related_nodes: list[UUID] = Field(default_factory=list, description="Related nodes")

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag. Returns True if tag existed."""
        try:
            self.tags.remove(tag)
            return True
        except ValueError:
            return False

    def has_tag(self, tag: str) -> bool:
        """Check if node has a specific tag."""
        return tag in self.tags

    def add_tags(self, tags: list[str]) -> None:
        """Add multiple tags."""
        for tag in tags:
            self.add_tag(tag)

    def clear_tags(self) -> None:
        """Clear all tags."""
        self.tags.clear()

    def get_tags_count(self) -> int:
        """Get count of tags."""
        return len(self.tags)

    def add_category(self, category: str) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def remove_category(self, category: str) -> bool:
        """Remove a category. Returns True if category existed."""
        try:
            self.categories.remove(category)
            return True
        except ValueError:
            return False

    def has_category(self, category: str) -> bool:
        """Check if node has a specific category."""
        return category in self.categories

    def add_categories(self, categories: list[str]) -> None:
        """Add multiple categories."""
        for category in categories:
            self.add_category(category)

    def clear_categories(self) -> None:
        """Clear all categories."""
        self.categories.clear()

    def get_categories_count(self) -> int:
        """Get count of categories."""
        return len(self.categories)

    def add_dependency(self, dependency_id: UUID) -> None:
        """Add a dependency if not already present."""
        if dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)

    def remove_dependency(self, dependency_id: UUID) -> bool:
        """Remove a dependency. Returns True if dependency existed."""
        try:
            self.dependencies.remove(dependency_id)
            return True
        except ValueError:
            return False

    def has_dependency(self, dependency_id: UUID) -> bool:
        """Check if node has a specific dependency."""
        return dependency_id in self.dependencies

    def clear_dependencies(self) -> None:
        """Clear all dependencies."""
        self.dependencies.clear()

    def get_dependencies_count(self) -> int:
        """Get count of dependencies."""
        return len(self.dependencies)

    def add_related_node(self, node_id: UUID) -> None:
        """Add a related node if not already present."""
        if node_id not in self.related_nodes:
            self.related_nodes.append(node_id)

    def remove_related_node(self, node_id: UUID) -> bool:
        """Remove a related node. Returns True if node existed."""
        try:
            self.related_nodes.remove(node_id)
            return True
        except ValueError:
            return False

    def has_related_node(self, node_id: UUID) -> bool:
        """Check if node has a specific related node."""
        return node_id in self.related_nodes

    def clear_related_nodes(self) -> None:
        """Clear all related nodes."""
        self.related_nodes.clear()

    def get_related_nodes_count(self) -> int:
        """Get count of related nodes."""
        return len(self.related_nodes)

    def has_relationships(self) -> bool:
        """Check if node has any relationships (dependencies or related nodes)."""
        return len(self.dependencies) > 0 or len(self.related_nodes) > 0

    def has_categorization(self) -> bool:
        """Check if node has any categorization (tags or categories)."""
        return len(self.tags) > 0 or len(self.categories) > 0

    def is_well_categorized(self, min_tags: int = 1, min_categories: int = 1) -> bool:
        """Check if node is well categorized."""
        return len(self.tags) >= min_tags and len(self.categories) >= min_categories

    def get_categorization_summary(self) -> dict[str, int | list[str]]:
        """Get categorization summary."""
        return {
            "tags_count": len(self.tags),
            "categories_count": len(self.categories),
            "dependencies_count": len(self.dependencies),
            "related_nodes_count": len(self.related_nodes),
            "tags": self.tags.copy(),
            "categories": self.categories.copy(),
        }

    def matches_tag_filter(self, required_tags: list[str]) -> bool:
        """Check if node matches all required tags."""
        return all(tag in self.tags for tag in required_tags)

    def matches_category_filter(self, required_categories: list[str]) -> bool:
        """Check if node matches all required categories."""
        return all(category in self.categories for category in required_categories)

    @classmethod
    def create_with_tags(cls, tags: list[str]) -> ModelNodeCategorization:
        """Create categorization with initial tags."""
        return cls(tags=tags.copy())

    @classmethod
    def create_with_categories(cls, categories: list[str]) -> ModelNodeCategorization:
        """Create categorization with initial categories."""
        return cls(categories=categories.copy())

    @classmethod
    def create_comprehensive(
        cls,
        tags: list[str],
        categories: list[str],
        dependencies: list[UUID] | None = None,
        related_nodes: list[UUID] | None = None,
    ) -> ModelNodeCategorization:
        """Create comprehensive categorization."""
        return cls(
            tags=tags.copy(),
            categories=categories.copy(),
            dependencies=dependencies.copy() if dependencies else [],
            related_nodes=related_nodes.copy() if related_nodes else [],
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Assign tags by reference (caller should not mutate)
        if self.tags:
            result["tags"] = self.tags
        # Pack other categorization fields into metadata dict
        result["metadata"] = {
            # Cast list[str] to list[JsonType] for type compatibility (zero-cost at runtime)
            "categories": cast(list[JsonType], self.categories),
            "dependencies": [str(dep) for dep in self.dependencies],
            "related_nodes": [str(node) for node in self.related_nodes],
            "tags_count": self.get_tags_count(),
            "categories_count": self.get_categories_count(),
            "dependencies_count": self.get_dependencies_count(),
            "related_nodes_count": self.get_related_nodes_count(),
            "has_relationships": self.has_relationships(),
            "has_categorization": self.has_categorization(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelNodeCategorization"]

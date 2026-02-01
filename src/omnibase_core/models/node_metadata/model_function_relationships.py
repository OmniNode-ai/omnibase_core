"""
Function Relationships Model.

Dependency and relationship information for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_function_relationships_summary import (
    TypedDictFunctionRelationshipsSummary,
)


class ModelFunctionRelationships(BaseModel):
    """
    Function dependency and relationship information.

    Contains relationship data:
    - Dependencies and related functions
    - Categorization and tagging
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Dependencies and relationships (2 fields)
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Function dependencies (UUIDs of dependent functions)",
    )
    related_functions: list[UUID] = Field(
        default_factory=list,
        description="Related functions (UUIDs of related functions)",
    )

    # Categorization (2 fields)
    tags: list[str] = Field(default_factory=list, description="Function tags")
    categories: list[EnumCategory] = Field(
        default_factory=list,
        description="Function categories",
    )

    def add_dependency(self, dependency: UUID) -> None:
        """Add a dependency."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def add_related_function(self, function_id: UUID) -> None:
        """Add a related function."""
        if function_id not in self.related_functions:
            self.related_functions.append(function_id)

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def add_category(self, category: EnumCategory) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def has_dependencies(self) -> bool:
        """Check if function has dependencies."""
        return len(self.dependencies) > 0

    def has_related_functions(self) -> bool:
        """Check if function has related functions."""
        return len(self.related_functions) > 0

    def has_tags(self) -> bool:
        """Check if function has tags."""
        return len(self.tags) > 0

    def has_categories(self) -> bool:
        """Check if function has categories."""
        return len(self.categories) > 0

    def get_relationships_summary(
        self,
    ) -> TypedDictFunctionRelationshipsSummary:
        """Get relationships summary."""
        return {
            "dependencies_count": len(self.dependencies),
            "related_functions_count": len(self.related_functions),
            "tags_count": len(self.tags),
            "categories_count": len(self.categories),
            "has_dependencies": self.has_dependencies(),
            "has_related_functions": self.has_related_functions(),
            "has_tags": self.has_tags(),
            "has_categories": self.has_categories(),
            "primary_category": (
                self.categories[0].value if self.categories else "None"
            ),
        }

    @classmethod
    def create_tagged(
        cls,
        tags: list[str],
        categories: list[EnumCategory] | None = None,
    ) -> ModelFunctionRelationships:
        """Create relationships with tags and categories."""
        return cls(
            tags=tags,
            categories=categories if categories is not None else [],
        )

    @classmethod
    def create_with_dependencies(
        cls,
        dependencies: list[UUID],
        related_functions: list[UUID] | None = None,
    ) -> ModelFunctionRelationships:
        """Create relationships with dependencies."""
        return cls(
            dependencies=dependencies,
            related_functions=related_functions
            if related_functions is not None
            else [],
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
        # Map tags to TypedDictMetadataDict structure
        if self.tags:
            result["tags"] = self.tags
        # Pack additional fields into metadata
        result["metadata"] = {
            "dependencies": [str(dep) for dep in self.dependencies],
            "related_functions": [str(func) for func in self.related_functions],
            "categories": [cat.value for cat in self.categories],
            "has_dependencies": self.has_dependencies(),
            "has_related_functions": self.has_related_functions(),
            "has_tags": self.has_tags(),
            "has_categories": self.has_categories(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelFunctionRelationships"]

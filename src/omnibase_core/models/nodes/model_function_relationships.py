from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Function Relationships Model.

Dependency and relationship information for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.types.typed_dict_function_relationships_summary import (
    TypedDictFunctionRelationshipsSummary,
)


class ModelFunctionRelationships(BaseModel):
    """
    Function dependency and relationship information.

    Contains relationship data:
    - Dependencies and related functions
    - Categorization and tagging
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
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
            categories=categories or [],
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
            related_functions=related_functions or [],
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
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
__all__ = ["ModelFunctionRelationships"]

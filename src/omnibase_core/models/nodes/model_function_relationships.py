"""
Function Relationships Model.

Dependency and relationship information for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_types_function_relationships_summary import FunctionRelationshipsSummaryType


class ModelFunctionRelationships(BaseModel):
    """
    Function dependency and relationship information.

    Contains relationship data:
    - Dependencies and related functions
    - Categorization and tagging
    """

    # Dependencies and relationships (2 fields)
    dependencies: list[str] = Field(
        default_factory=list,
        description="Function dependencies",
    )
    related_functions: list[str] = Field(
        default_factory=list,
        description="Related functions",
    )

    # Categorization (2 fields)
    tags: list[str] = Field(default_factory=list, description="Function tags")
    categories: list[str] = Field(
        default_factory=list,
        description="Function categories",
    )

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def add_related_function(self, function_name: str) -> None:
        """Add a related function."""
        if function_name not in self.related_functions:
            self.related_functions.append(function_name)

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def add_category(self, category: str) -> None:
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
    ) -> FunctionRelationshipsSummaryType:
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
            "primary_category": self.categories[0] if self.categories else "None",
        }

    @classmethod
    def create_tagged(
        cls,
        tags: list[str],
        categories: list[str] | None = None,
    ) -> ModelFunctionRelationships:
        """Create relationships with tags and categories."""
        return cls(
            tags=tags,
            categories=categories or [],
        )

    @classmethod
    def create_with_dependencies(
        cls,
        dependencies: list[str],
        related_functions: list[str] | None = None,
    ) -> ModelFunctionRelationships:
        """Create relationships with dependencies."""
        return cls(
            dependencies=dependencies,
            related_functions=related_functions or [],
        )


# Export for use
__all__ = ["ModelFunctionRelationships"]

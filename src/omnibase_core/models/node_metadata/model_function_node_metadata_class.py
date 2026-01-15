"""Function Node Metadata Model.

Documentation and metadata for function nodes.
Part of the ModelFunctionNode restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_documentation_summary_filtered import (
    TypedDictDocumentationSummaryFiltered,
)
from omnibase_core.types.typed_dict_function_metadata_summary import (
    TypedDictFunctionMetadataSummary,
)

from .model_function_deprecation_info import ModelFunctionDeprecationInfo
from .model_function_documentation import ModelFunctionDocumentation
from .model_function_relationships import ModelFunctionRelationships


class ModelFunctionNodeMetadata(BaseModel):
    """
    Function node metadata and documentation.

    Restructured to use focused sub-models for better organization.
    """

    # Composed sub-models (3 primary components)
    documentation: ModelFunctionDocumentation = Field(
        default_factory=lambda: ModelFunctionDocumentation(),
        description="Documentation and examples",
    )
    deprecation: ModelFunctionDeprecationInfo = Field(
        default_factory=lambda: ModelFunctionDeprecationInfo(),
        description="Deprecation information",
    )
    relationships: ModelFunctionRelationships = Field(
        default_factory=lambda: ModelFunctionRelationships(),
        description="Dependencies and relationships",
    )

    # Timestamps (3 fields)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Custom properties for extensibility
    custom_properties: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Custom properties with type safety",
    )

    # Delegation properties
    @property
    def docstring(self) -> str | None:
        """Function docstring (delegated to documentation)."""
        return self.documentation.docstring

    @docstring.setter
    def docstring(self, value: str | None) -> None:
        """Set function docstring."""
        self.documentation.docstring = value

    @property
    def examples(self) -> list[str]:
        """Usage examples (delegated to documentation)."""
        return self.documentation.examples

    @property
    def notes(self) -> list[str]:
        """Additional notes (delegated to documentation)."""
        return self.documentation.notes

    @property
    def deprecated_since(self) -> str | None:
        """Deprecated since version as string."""
        return (
            str(self.deprecation.deprecated_since)
            if self.deprecation.deprecated_since
            else None
        )

    @deprecated_since.setter
    def deprecated_since(self, value: str | None) -> None:
        """Set deprecated since version from string."""
        if value is None:
            self.deprecation.deprecated_since = None
        else:
            try:
                # Try to parse as semver
                parts = value.split(".")
                if len(parts) >= 2:
                    major = int(parts[0])
                    minor = int(parts[1])
                    patch = int(parts[2]) if len(parts) > 2 else 0
                    self.deprecation.deprecated_since = ModelSemVer(
                        major=major,
                        minor=minor,
                        patch=patch,
                    )
                else:
                    # Fallback for simple version strings
                    self.deprecation.deprecated_since = ModelSemVer(
                        major=1,
                        minor=0,
                        patch=0,
                    )
            except (IndexError, ValueError):
                self.deprecation.deprecated_since = ModelSemVer(
                    major=1,
                    minor=0,
                    patch=0,
                )

    @property
    def replacement(self) -> str | None:
        """Replacement function (delegated to deprecation)."""
        return self.deprecation.replacement

    @replacement.setter
    def replacement(self, value: str | None) -> None:
        """Set replacement function."""
        self.deprecation.replacement = value

    @property
    def tags(self) -> list[str]:
        """Function tags (delegated to relationships)."""
        return self.relationships.tags

    @property
    def categories(self) -> list[EnumCategory]:
        """Function categories (delegated to relationships)."""
        return self.relationships.categories

    @property
    def dependencies(self) -> list[UUID]:
        """Function dependencies (delegated to relationships)."""
        return self.relationships.dependencies

    @property
    def related_functions(self) -> list[UUID]:
        """Related functions (delegated to relationships)."""
        return self.relationships.related_functions

    def has_documentation(self) -> bool:
        """Check if function has adequate documentation."""
        return self.documentation.has_documentation()

    def has_examples(self) -> bool:
        """Check if function has usage examples."""
        return self.documentation.has_examples()

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        self.relationships.add_tag(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        self.relationships.remove_tag(tag)

    def add_category(self, category: EnumCategory) -> None:
        """Add a category if not already present."""
        self.relationships.add_category(category)

    def add_example(self, example: str) -> None:
        """Add a usage example."""
        self.documentation.add_example(example)

    def add_note(self, note: str) -> None:
        """Add a note."""
        self.documentation.add_note(note)

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency."""
        # Convert string to UUID - assume it's a UUID string or generate one from hash
        try:
            dependency_uuid = UUID(dependency)
        except ValueError:
            # If not a valid UUID string, generate one from the hash of the string
            # Use SHA-256 for security (MD5 is deprecated) and take first 32 chars for UUID
            hash_hex = sha256(dependency.encode()).hexdigest()[:32]
            dependency_uuid = UUID(hash_hex)
        self.relationships.add_dependency(dependency_uuid)

    def add_related_function(self, function_name: str) -> None:
        """Add a related function."""
        # Convert string to UUID - assume it's a UUID string or generate one from hash
        try:
            function_uuid = UUID(function_name)
        except ValueError:
            # If not a valid UUID string, generate one from the hash of the string
            # Use SHA-256 for security (MD5 is deprecated) and take first 32 chars for UUID
            hash_hex = sha256(function_name.encode()).hexdigest()[:32]
            function_uuid = UUID(hash_hex)
        self.relationships.add_related_function(function_uuid)

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    def mark_validated(self) -> None:
        """Mark function as validated."""
        self.last_validated = datetime.now(UTC)

    def is_recently_updated(self, days: int = 30) -> bool:
        """Check if function was updated recently."""
        if not self.updated_at:
            return False
        delta = datetime.now(UTC) - self.updated_at
        return delta.days <= days

    def get_documentation_quality_score(self) -> float:
        """Get documentation quality score (0-1)."""
        doc_score = self.documentation.get_documentation_quality_score() * 0.6
        rel_score = 0.0

        # Categories and tags
        if self.relationships.has_categories() or self.relationships.has_tags():
            rel_score += 0.2

        # Relationships
        if (
            self.relationships.has_dependencies()
            or self.relationships.has_related_functions()
        ):
            rel_score += 0.2

        return min(doc_score + rel_score, 1.0)

    def get_metadata_summary(self) -> TypedDictFunctionMetadataSummary:
        """Get comprehensive metadata summary."""
        doc_summary = self.documentation.get_documentation_summary()
        dep_summary = self.deprecation.get_deprecation_summary()
        rel_summary = self.relationships.get_relationships_summary()

        # Convert documentation summary to expected format (exclude quality_score - handled separately)
        doc_filtered: TypedDictDocumentationSummaryFiltered = {
            "has_documentation": doc_summary.get("has_documentation", False),
            "has_examples": doc_summary.get("has_examples", False),
            "has_notes": doc_summary.get("has_notes", False),
            "examples_count": doc_summary.get("examples_count", 0),
            "notes_count": doc_summary.get("notes_count", 0),
        }

        # Convert relationships summary to ModelMetadataValue format
        rel_converted = {
            key: ModelMetadataValue.from_any(value)
            for key, value in rel_summary.items()
        }

        return TypedDictFunctionMetadataSummary(
            documentation=doc_filtered,
            deprecation=dep_summary,
            relationships=rel_converted,  # type: ignore[typeddict-item]
            documentation_quality_score=self.get_documentation_quality_score(),
            # Consider "fully documented" based on documentation, not recency
            is_fully_documented=(
                doc_filtered.get("has_documentation", False)
                and doc_filtered.get("has_examples", False)
            ),
            deprecation_status=self.deprecation.get_deprecation_status().value,
        )

    @classmethod
    def create_documented(
        cls,
        docstring: str,
        examples: list[str] | None = None,
    ) -> ModelFunctionNodeMetadata:
        """Create metadata with documentation."""
        doc = ModelFunctionDocumentation.create_documented(docstring, examples)
        return cls(documentation=doc)

    @classmethod
    def create_tagged(
        cls,
        tags: list[str],
        categories: list[EnumCategory] | None = None,
    ) -> ModelFunctionNodeMetadata:
        """Create metadata with tags and categories."""
        rel = ModelFunctionRelationships.create_tagged(tags, categories)
        return cls(relationships=rel)

    @classmethod
    def create_deprecated(
        cls,
        deprecated_since: str,
        replacement: str | None = None,
    ) -> ModelFunctionNodeMetadata:
        """Create metadata for function with deprecation info."""

        # Parse version string
        try:
            parts = deprecated_since.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            version = ModelSemVer(major=major, minor=minor, patch=patch)
        except (IndexError, ValueError):
            version = ModelSemVer(major=1, minor=0, patch=0)

        dep = ModelFunctionDeprecationInfo.create_deprecated(version, replacement)
        return cls(deprecation=dep)

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

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Map tags to TypedDictMetadataDict structure via delegated property
        if self.tags:
            result["tags"] = self.tags
        # Pack additional fields into metadata
        result["metadata"] = {
            "has_documentation": self.has_documentation(),
            "has_examples": self.has_examples(),
            "deprecated_since": self.deprecated_since,
            "replacement": self.replacement,
            "categories": [cat.value for cat in self.categories],
            "dependencies": [str(dep) for dep in self.dependencies],
            "related_functions": [str(func) for func in self.related_functions],
            "documentation_quality_score": self.get_documentation_quality_score(),
            "is_recently_updated": self.is_recently_updated(),
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


# NOTE: model_rebuild() not needed - Pydantic v2 handles forward references automatically
# ModelMetadataValue is imported at runtime, Pydantic will resolve references lazily

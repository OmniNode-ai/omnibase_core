"""
Structured Tags Model.

Provides structured tag management with standard and custom tags.
Reduces reliance on unstructured string tag list[Any]s.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelStructuredTags(BaseModel):
    """
    Structured tag management with standard and custom tags.

    Provides organized tagging with validation and categorization
    while maintaining flexibility for custom tags.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identity
    tags_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "tags"),
        description="Unique identifier for this tag collection",
    )

    # Standard tags (strongly typed)
    standard_tags: list[EnumStandardTag] = Field(
        default_factory=list,
        description="Standard classification tags",
        max_length=10,
    )

    # Category-based organization
    primary_category: EnumStandardCategory | None = Field(
        default=None,
        description="Primary category for organization",
    )

    secondary_categories: list[EnumStandardCategory] = Field(
        default_factory=list,
        description="Secondary categories for cross-classification",
        max_length=3,
    )

    # Custom tags (validated)
    custom_tags: list[str] = Field(
        default_factory=list,
        description="Custom tags following naming conventions",
        max_length=5,
    )

    # Domain-specific tags
    domain_tags: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Domain-specific tag collections",
    )

    # Tag metadata
    tag_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the tag schema",
    )

    is_validated: bool = Field(
        default=False,
        description="Whether tags have been validated",
    )

    @property
    def all_tags(self) -> list[str]:
        """Get all tags as strings."""
        tags = [tag.value for tag in self.standard_tags]
        tags.extend(self.custom_tags)

        # Add domain tags
        for domain_tag_list in self.domain_tags.values():
            tags.extend(domain_tag_list)

        return sorted(set(tags))  # Remove duplicates and sort

    @property
    def functional_tags(self) -> list[EnumStandardTag]:
        """Get functional classification tags."""
        return [
            tag
            for tag in self.standard_tags
            if tag in EnumStandardTag.get_functional_tags()
        ]

    @property
    def complexity_tags(self) -> list[EnumStandardTag]:
        """Get complexity classification tags."""
        return [
            tag
            for tag in self.standard_tags
            if tag in EnumStandardTag.get_complexity_tags()
        ]

    @property
    def domain_classification_tags(self) -> list[EnumStandardTag]:
        """Get domain classification tags."""
        return [
            tag
            for tag in self.standard_tags
            if tag in EnumStandardTag.get_domain_tags()
        ]

    @property
    def quality_tags(self) -> list[EnumStandardTag]:
        """Get quality classification tags."""
        return [
            tag
            for tag in self.standard_tags
            if tag in EnumStandardTag.get_quality_tags()
        ]

    def add_standard_tag(self, tag: EnumStandardTag) -> bool:
        """Add a standard tag if not already present and within limits."""
        if tag not in self.standard_tags and len(self.standard_tags) < 10:
            self.standard_tags.append(tag)
            return True
        return False

    def remove_standard_tag(self, tag: EnumStandardTag) -> bool:
        """Remove a standard tag if present."""
        if tag in self.standard_tags:
            self.standard_tags.remove(tag)
            return True
        return False

    def add_custom_tag(self, tag: str) -> bool:
        """Add a custom tag with validation."""
        # Validate custom tag format
        if not self._is_valid_custom_tag(tag):
            return False

        if tag not in self.custom_tags and len(self.custom_tags) < 5:
            self.custom_tags.append(tag)
            return True
        return False

    def remove_custom_tag(self, tag: str) -> bool:
        """Remove a custom tag if present."""
        if tag in self.custom_tags:
            self.custom_tags.remove(tag)
            return True
        return False

    def add_domain_tag(self, domain: str, tag: str) -> bool:
        """Add a domain-specific tag."""
        if domain not in self.domain_tags:
            self.domain_tags[domain] = []

        if tag not in self.domain_tags[domain]:
            self.domain_tags[domain].append(tag)
            return True
        return False

    def remove_domain_tag(self, domain: str, tag: str) -> bool:
        """Remove a domain-specific tag."""
        if domain in self.domain_tags and tag in self.domain_tags[domain]:
            self.domain_tags[domain].remove(tag)
            # Clean up empty domain
            if not self.domain_tags[domain]:
                del self.domain_tags[domain]
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if any tag (standard or custom) matches."""
        return tag in self.all_tags

    def has_standard_tag(self, tag: EnumStandardTag) -> bool:
        """Check if standard tag is present."""
        return tag in self.standard_tags

    def has_category(self, category: EnumStandardCategory) -> bool:
        """Check if category is present (primary or secondary)."""
        return (
            self.primary_category == category or category in self.secondary_categories
        )

    def get_tags_by_category(self, category: str) -> list[str]:
        """Get tags for a specific category."""
        if category == "functional":
            return [tag.value for tag in self.functional_tags]
        if category == "complexity":
            return [tag.value for tag in self.complexity_tags]
        if category == "domain":
            return [tag.value for tag in self.domain_classification_tags]
        if category == "quality":
            return [tag.value for tag in self.quality_tags]
        if category in self.domain_tags:
            return self.domain_tags[category].copy()
        return []

    def validate_tags(self) -> bool:
        """Validate all tags and mark as validated."""
        # Check for conflicting tags
        complexity_tags = self.complexity_tags
        if len(complexity_tags) > 1:
            return False  # Can't have multiple complexity levels

        # Validate custom tags
        for tag in self.custom_tags:
            if not self._is_valid_custom_tag(tag):
                return False

        self.is_validated = True
        return True

    def _is_valid_custom_tag(self, tag: str) -> bool:
        """Validate custom tag format."""
        # Must be lowercase alphanumeric with underscores
        if not tag.replace("_", "").replace("-", "").isalnum():
            return False

        # Must start with letter
        if not tag[0].isalpha():
            return False

        # Reasonable length
        if len(tag) < 2 or len(tag) > 30:
            return False

        # Check against standard tags to avoid duplication
        for standard_tag in EnumStandardTag:
            if tag == standard_tag.value:
                return False

        return True

    @classmethod
    def from_string_list(
        cls,
        tags: list[str],
        primary_category: EnumStandardCategory | None = None,
    ) -> ModelStructuredTags:
        """Create structured tags from string list[Any]."""
        structured = cls(
            tags_id=uuid_from_string("_".join(sorted(tags[:3])), "tags"),
            primary_category=primary_category,
            tag_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        for tag in tags:
            # Try to convert to standard tag
            standard_tag = EnumStandardTag.from_string(tag)
            if standard_tag:
                structured.add_standard_tag(standard_tag)
            else:
                # Add as custom tag if valid
                structured.add_custom_tag(tag)

        structured.validate_tags()
        return structured

    @classmethod
    def for_metadata_node(
        cls,
        complexity: EnumStandardTag | None = None,
        domain: EnumStandardTag | None = None,
        custom_tags: list[str] | None = None,
    ) -> ModelStructuredTags:
        """Create structured tags for metadata nodes."""
        standard_tags = [EnumStandardTag.CORE, EnumStandardTag.DOCUMENTED]

        if complexity:
            standard_tags.append(complexity)

        if domain:
            standard_tags.append(domain)

        structured = cls(
            tags_id=uuid_from_string("metadata_node_tags", "tags"),
            standard_tags=standard_tags,
            primary_category=EnumStandardCategory.DATA_PROCESSING,
            custom_tags=custom_tags if custom_tags is not None else [],
            tag_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        structured.validate_tags()
        return structured

    @classmethod
    def for_function_node(
        cls,
        function_category: EnumStandardCategory | None = None,
        complexity: EnumStandardTag | None = None,
        custom_tags: list[str] | None = None,
    ) -> ModelStructuredTags:
        """Create structured tags for function nodes."""
        standard_tags = [EnumStandardTag.CORE, EnumStandardTag.TESTED]

        if complexity:
            standard_tags.append(complexity)

        structured = cls(
            tags_id=uuid_from_string("function_node_tags", "tags"),
            standard_tags=standard_tags,
            primary_category=function_category or EnumStandardCategory.BUSINESS_LOGIC,
            custom_tags=custom_tags if custom_tags is not None else [],
            tag_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        structured.validate_tags()
        return structured

    @classmethod
    def for_analytics(
        cls,
        monitored: bool = True,
        custom_tags: list[str] | None = None,
    ) -> ModelStructuredTags:
        """Create structured tags for analytics objects."""
        standard_tags = [EnumStandardTag.CORE]

        if monitored:
            standard_tags.append(EnumStandardTag.MONITORED)

        structured = cls(
            tags_id=uuid_from_string("analytics_tags", "tags"),
            standard_tags=standard_tags,
            primary_category=EnumStandardCategory.ANALYTICS,
            custom_tags=custom_tags if custom_tags is not None else [],
            tag_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        structured.validate_tags()
        return structured

    def __str__(self) -> str:
        """String representation returns comma-separated tags."""
        return ", ".join(self.all_tags)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # tag_version is required field (no default), always present
        result["version"] = self.tag_version
        all_tags = self.all_tags
        if all_tags:
            result["tags"] = all_tags
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
__all__ = ["ModelStructuredTags"]

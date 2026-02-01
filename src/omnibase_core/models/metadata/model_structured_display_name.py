"""
Structured Display Name Model.

Provides consistent naming patterns across metadata models.
Reduces reliance on free-form display name strings.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelStructuredDisplayName(BaseModel):
    """
    Structured display name with consistent naming patterns.

    Replaces free-form display name strings with structured naming
    that follows ONEX conventions and provides better categorization.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identity
    name_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "name"),
        description="Unique identifier for this display name",
    )

    # Base name components
    base_name: str = Field(
        default=...,
        description="Base name without prefixes or suffixes",
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    # Optional naming components
    prefix: str | None = Field(
        default=None,
        description="Optional prefix (e.g., 'metadata_', 'node_')",
        pattern=r"^[a-z][a-z0-9_]*_$",
    )

    suffix: str | None = Field(
        default=None,
        description="Optional suffix (e.g., '_info', '_summary')",
        pattern=r"^_[a-z][a-z0-9_]*$",
    )

    # Categorization
    primary_category: EnumStandardCategory | None = Field(
        default=None,
        description="Primary category for this entity",
    )

    primary_tag: EnumStandardTag | None = Field(
        default=None,
        description="Primary classification tag",
    )

    # Version and environment context
    version: ModelSemVer | None = Field(
        default=None,
        description="Semantic version for this entity",
    )

    environment_prefix: str | None = Field(
        default=None,
        description="Environment-specific prefix (e.g., 'dev_', 'prod_')",
        pattern=r"^(dev|test|staging|prod)_$",
    )

    @property
    def display_name(self) -> str:
        """Generate the full display name from components."""
        components = []

        # Add environment prefix if present
        if self.environment_prefix:
            components.append(self.environment_prefix.rstrip("_"))

        # Add prefix if present
        if self.prefix:
            components.append(self.prefix.rstrip("_"))

        # Add base name
        components.append(self.base_name)

        # Add suffix if present
        if self.suffix:
            components.append(self.suffix.lstrip("_"))

        # Add version if present
        if self.version:
            components.append(f"v{self.version}")

        return "_".join(components)

    @property
    def human_readable_name(self) -> str:
        """Generate human-readable version of the name."""
        # Convert snake_case to Title Case
        words = self.display_name.replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)

    @property
    def category_qualified_name(self) -> str:
        """Get name qualified with category information."""
        if self.primary_category:
            return f"{self.primary_category.value}:{self.display_name}"
        return self.display_name

    @classmethod
    def from_plain_string(
        cls,
        name: str,
        category: EnumStandardCategory | None = None,
        tag: EnumStandardTag | None = None,
    ) -> ModelStructuredDisplayName:
        """Create structured name from plain string."""
        # Parse common patterns
        parsed_prefix = None
        parsed_suffix = None
        base = name.lower().strip()

        # Extract common prefixes
        common_prefixes = ["metadata_", "node_", "model_", "enum_", "config_"]
        for prefix in common_prefixes:
            if base.startswith(prefix):
                parsed_prefix = prefix
                base = base[len(prefix) :]
                break

        # Extract common suffixes
        common_suffixes = ["_info", "_summary", "_data", "_config", "_metrics"]
        for suffix in common_suffixes:
            if base.endswith(suffix):
                parsed_suffix = suffix
                base = base[: -len(suffix)]
                break

        return cls(
            name_id=uuid_from_string(name, "structured_name"),
            base_name=base,
            prefix=parsed_prefix,
            suffix=parsed_suffix,
            primary_category=category,
            primary_tag=tag,
        )

    @classmethod
    def for_metadata_node(
        cls,
        base_name: str,
        category: EnumStandardCategory | None = None,
    ) -> ModelStructuredDisplayName:
        """Create structured name for metadata nodes."""
        return cls(
            name_id=uuid_from_string(f"metadata_node_{base_name}", "structured_name"),
            base_name=base_name,
            prefix="metadata_",
            suffix="_node",
            primary_category=category or EnumStandardCategory.DATA_PROCESSING,
            primary_tag=EnumStandardTag.CORE,
        )

    @classmethod
    def for_function_node(
        cls,
        base_name: str,
        category: EnumStandardCategory | None = None,
    ) -> ModelStructuredDisplayName:
        """Create structured name for function nodes."""
        return cls(
            name_id=uuid_from_string(f"function_{base_name}", "structured_name"),
            base_name=base_name,
            prefix="function_",
            primary_category=category or EnumStandardCategory.BUSINESS_LOGIC,
            primary_tag=EnumStandardTag.CORE,
        )

    @classmethod
    def for_analytics_summary(
        cls,
        base_name: str,
    ) -> ModelStructuredDisplayName:
        """Create structured name for analytics summaries."""
        return cls(
            name_id=uuid_from_string(f"analytics_{base_name}", "structured_name"),
            base_name=base_name,
            prefix="analytics_",
            suffix="_summary",
            primary_category=EnumStandardCategory.ANALYTICS,
            primary_tag=EnumStandardTag.MONITORED,
        )

    @classmethod
    def for_configuration(
        cls,
        base_name: str,
        environment: str | None = None,
    ) -> ModelStructuredDisplayName:
        """Create structured name for configuration objects."""
        env_prefix = f"{environment}_" if environment else None
        return cls(
            name_id=uuid_from_string(f"config_{base_name}", "structured_name"),
            base_name=base_name,
            prefix="config_",
            environment_prefix=env_prefix,
            primary_category=EnumStandardCategory.CONFIGURATION,
            primary_tag=EnumStandardTag.CORE,
        )

    def with_version(self, version: ModelSemVer) -> ModelStructuredDisplayName:
        """Create a version-specific variant of this name."""
        return ModelStructuredDisplayName(
            name_id=uuid_from_string(
                f"{self.display_name}_v{version}",
                "structured_name",
            ),
            base_name=self.base_name,
            prefix=self.prefix,
            suffix=self.suffix,
            primary_category=self.primary_category,
            primary_tag=self.primary_tag,
            version=version,
            environment_prefix=self.environment_prefix,
        )

    def with_environment(self, environment: str) -> ModelStructuredDisplayName:
        """Create an environment-specific variant of this name."""
        env_prefix = f"{environment}_"

        return ModelStructuredDisplayName(
            name_id=uuid_from_string(
                f"{env_prefix}{self.display_name}",
                "structured_name",
            ),
            base_name=self.base_name,
            prefix=self.prefix,
            suffix=self.suffix,
            primary_category=self.primary_category,
            primary_tag=self.primary_tag,
            version=self.version,
            environment_prefix=env_prefix,
        )

    def is_compatible_with(self, other: ModelStructuredDisplayName) -> bool:
        """Check if this name is compatible with another (same base, different variants)."""
        return (
            self.base_name == other.base_name
            and self.prefix == other.prefix
            and self.suffix == other.suffix
            and self.primary_category == other.primary_category
        )

    def __str__(self) -> str:
        """String representation returns the display name."""
        return self.display_name

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # display_name always returns non-empty string (includes required base_name)
        result["name"] = self.display_name
        if self.version is not None:
            result["version"] = self.version
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except PYDANTIC_MODEL_ERRORS as e:
            # boundary-ok: transform dynamic attribute access errors to typed domain errors
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Basic validation - base implementation always returns True.
        # Subclasses should override with actual validation logic.
        return True


# Export for use
__all__ = ["ModelStructuredDisplayName"]

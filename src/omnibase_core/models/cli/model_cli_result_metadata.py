"""
CLI result metadata model.

Clean, strongly-typed replacement for dict[str, Any] in CLI result metadata.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.enums.enum_result_category import EnumResultCategory
from omnibase_core.enums.enum_result_type import EnumResultType
from omnibase_core.enums.enum_retention_policy import EnumRetentionPolicy
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.utils.util_uuid_utilities import uuid_from_string

# Using ModelValue instead of primitive soup type alias for proper discriminated union typing


class ModelCliResultMetadata(BaseModel):
    """
    Clean model for CLI result metadata.

    Replaces ModelGenericMetadata[Any] with structured metadata model.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Core metadata fields
    metadata_version: ModelSemVer | None = Field(
        default=None,
        description="Metadata schema version",
    )

    # Result identification
    result_type: EnumResultType = Field(
        default=EnumResultType.INFO,
        description="Type of result",
    )
    result_category: EnumResultCategory | None = Field(
        default=None,
        description="Result category",
    )

    # Source information
    source_command: str | None = Field(default=None, description="Source command")
    source_node: str | None = Field(default=None, description="Source node")

    # Processing metadata
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When result was processed",
    )
    processor_version: ModelSemVer | None = Field(
        default=None, description="Processor version"
    )

    # Quality metrics
    quality_score: float | None = Field(
        default=None,
        description="Quality score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    confidence_level: float | None = Field(
        default=None,
        description="Confidence level (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    # Data classification
    data_classification: EnumDataClassification = Field(
        default=EnumDataClassification.INTERNAL,
        description="Data classification level",
    )
    retention_policy: EnumRetentionPolicy | None = Field(
        default=None,
        description="Data retention policy",
    )

    # Tags and labels - UUID-based entity references
    tags: list[str] = Field(default_factory=list, description="Result tags")
    label_ids: dict[UUID, str] = Field(
        default_factory=dict,
        description="Label UUID to value mapping",
    )
    label_names: dict[str, UUID] = Field(
        default_factory=dict,
        description="Label name to UUID mapping",
    )

    # Performance metrics
    processing_time_ms: float | None = Field(
        default=None,
        description="Processing time in milliseconds",
    )
    resource_usage: dict[str, float] = Field(
        default_factory=dict,
        description="Resource usage metrics",
    )

    # Compliance and audit
    compliance_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Compliance flags",
    )
    audit_trail: list[str] = Field(
        default_factory=list,
        description="Audit trail entries",
    )

    # Custom metadata fields for extensibility
    custom_metadata: dict[str, ModelValue] = Field(
        default_factory=dict,
        description="Custom metadata fields",
    )

    @field_validator("processor_version", mode="before")
    @classmethod
    def validate_processor_version(cls, v: object) -> ModelSemVer | None:
        """Convert string processor version to ModelSemVer or return ModelSemVer as-is."""
        if v is None:
            return None
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            # Parse version string like "1.0.0"
            parts = v.split(".")
            if len(parts) >= 3:
                return ModelSemVer(
                    major=int(parts[0]),
                    minor=int(parts[1]),
                    patch=int(parts[2]),
                )
            if len(parts) == 2:
                return ModelSemVer(major=int(parts[0]), minor=int(parts[1]), patch=0)
            if len(parts) == 1:
                return ModelSemVer(major=int(parts[0]), minor=0, patch=0)
            raise ModelOnexError(
                message=f"Invalid version string: {v}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        raise ModelOnexError(
            message=f"Invalid processor version type: {type(v)}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    @field_validator("retention_policy", mode="before")
    @classmethod
    def validate_retention_policy(cls, v: object) -> EnumRetentionPolicy | None:
        """Convert string retention policy to enum or return enum as-is."""
        if v is None:
            return None
        if isinstance(v, EnumRetentionPolicy):
            return v
        if isinstance(v, str):
            try:
                return EnumRetentionPolicy(v)
            except ValueError:
                # Try uppercase
                try:
                    return EnumRetentionPolicy(v.upper())
                except ValueError:
                    raise ModelOnexError(
                        message=f"Invalid retention policy: {v}",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
        raise ModelOnexError(
            message=f"Invalid retention policy type: {type(v)}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    @field_validator("custom_metadata", mode="before")
    @classmethod
    def validate_custom_metadata(cls, v: dict[str, object]) -> dict[str, ModelValue]:
        """Validate custom metadata values ensure they are ModelValue objects."""
        result = {}
        for key, value in v.items():
            if isinstance(value, ModelValue):
                # Keep as ModelValue
                result[key] = value
            elif (
                isinstance(value, dict)
                and "value_type" in value
                and "raw_value" in value
            ):
                # Reconstruct ModelValue from serialized form
                result[key] = ModelValue.model_validate(value)
            else:
                # Convert to ModelValue
                result[key] = ModelValue.from_any(value)
        return result

    def add_tag(self, tag: str) -> None:
        """Add a tag to the result."""
        if tag not in self.tags:
            self.tags.append(tag)

    @property
    def labels(self) -> dict[str, str]:
        """Get labels as string-to-string mapping."""
        result = {}
        for name, uuid_id in self.label_names.items():
            if uuid_id in self.label_ids:
                result[name] = self.label_ids[uuid_id]
        return result

    def add_label(self, key: str, value: str) -> None:
        """Add a label to the result."""
        uuid_id = uuid_from_string(key, "label")
        self.label_ids[uuid_id] = value
        self.label_names[key] = uuid_id

    def get_label(self, key: str) -> str | None:
        """Get label value by name."""
        uuid_id = self.label_names.get(key)
        if uuid_id:
            return self.label_ids.get(uuid_id)
        return None

    def remove_label(self, key: str) -> bool:
        """Remove label by name. Returns True if removed, False if not found."""
        uuid_id = self.label_names.get(key)
        if uuid_id:
            self.label_ids.pop(uuid_id, None)
            self.label_names.pop(key, None)
            return True
        return False

    def set_quality_score(self, score: float) -> None:
        """Set the quality score."""
        if 0.0 <= score <= 1.0:
            self.quality_score = score
        else:
            raise ModelOnexError(
                message="Quality score must be between 0.0 and 1.0",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def set_confidence_level(self, confidence: float) -> None:
        """Set the confidence level."""
        if 0.0 <= confidence <= 1.0:
            self.confidence_level = confidence
        else:
            raise ModelOnexError(
                message="Confidence level must be between 0.0 and 1.0",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def add_resource_usage(self, resource: str, usage: float) -> None:
        """Add resource usage information."""
        self.resource_usage[resource] = usage

    def set_compliance_flag(self, flag: str, value: bool) -> None:
        """Set a compliance flag."""
        self.compliance_flags[flag] = value

    def add_audit_entry(self, entry: str) -> None:
        """Add an audit trail entry."""
        timestamp = datetime.now(UTC).isoformat()
        self.audit_trail.append(f"{timestamp}: {entry}")

    def set_custom_field(self, key: str, value: ModelValue | object) -> None:
        """Set a custom metadata field with automatic type conversion."""
        if isinstance(value, ModelValue):
            self.custom_metadata[key] = value
        else:
            # Convert to ModelValue for type safety
            self.custom_metadata[key] = ModelValue.from_any(value)

    def get_custom_field(
        self,
        key: str,
        default: ModelValue | None = None,
    ) -> ModelValue | None:
        """Get a custom metadata field with original type."""
        return self.custom_metadata.get(key, default)

    def is_compliant(self) -> bool:
        """Check if all compliance flags are True."""
        return all(self.compliance_flags.values()) if self.compliance_flags else True

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_labels_field(cls, data: object) -> object:
        """
        Transform legacy 'labels' field to new label_ids/label_names structure.

        This validator runs before Pydantic validation and handles backward
        compatibility with old CLI result metadata that used a simple dict[str, str]
        for labels instead of the new UUID-based dual mapping.
        """
        if isinstance(data, dict) and "labels" in data:
            # Create copy to avoid mutating input
            data = data.copy()
            labels = data.pop("labels")

            if isinstance(labels, dict):
                label_ids = {}
                label_names = {}
                for key, value in labels.items():
                    uuid_id = uuid_from_string(key, "label")
                    label_ids[uuid_id] = value
                    label_names[key] = uuid_id

                data["label_ids"] = label_ids
                data["label_names"] = label_names

        return data

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=True,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e


__all__ = ["ModelCliResultMetadata"]

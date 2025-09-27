"""
CLI result metadata model.

Clean, strongly-typed replacement for dict[str, Any] in CLI result metadata.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.enums.enum_result_category import EnumResultCategory
from omnibase_core.enums.enum_result_type import EnumResultType
from omnibase_core.enums.enum_retention_policy import EnumRetentionPolicy
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue
from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.utils.uuid_utilities import uuid_from_string


class ModelCliResultMetadata(BaseModel):
    """
    Clean model for CLI result metadata.

    Replaces ModelGenericMetadata[Any] with structured metadata model.
    """

    # Core metadata fields
    metadata_version: ModelSemVer | None = Field(
        None,
        description="Metadata schema version",
    )

    # Result identification
    result_type: EnumResultType = Field(
        default=EnumResultType.INFO,
        description="Type of result",
    )
    result_category: EnumResultCategory | None = Field(
        None,
        description="Result category",
    )

    # Source information
    source_command: str | None = Field(None, description="Source command")
    source_node: str | None = Field(None, description="Source node")

    # Processing metadata
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When result was processed",
    )
    processor_version: Union[ModelSemVer, str, None] = Field(
        None, description="Processor version"
    )

    # Quality metrics
    quality_score: float | None = Field(
        None,
        description="Quality score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    confidence_level: float | None = Field(
        None,
        description="Confidence level (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    # Data classification
    data_classification: Union[EnumDataClassification, str] = Field(
        default=EnumDataClassification.INTERNAL,
        description="Data classification level",
    )
    retention_policy: Union[EnumRetentionPolicy, str, None] = Field(
        None,
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
        None,
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
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata fields",
    )

    @field_validator("processor_version")
    @classmethod
    def validate_processor_version(
        cls, v: Union[ModelSemVer, str, None]
    ) -> ModelSemVer | None:
        """Convert string processor version to ModelSemVer."""
        if v is None:
            return None
        elif isinstance(v, str):
            # Parse version string like "1.0.0"
            parts = v.split(".")
            if len(parts) >= 3:
                return ModelSemVer(
                    major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
                )
            elif len(parts) == 2:
                return ModelSemVer(major=int(parts[0]), minor=int(parts[1]), patch=0)
            elif len(parts) == 1:
                return ModelSemVer(major=int(parts[0]), minor=0, patch=0)
            else:
                raise ValueError(f"Invalid version string: {v}")
        elif isinstance(v, ModelSemVer):
            return v
        else:
            # This should never happen with proper typing, but handle gracefully
            raise ValueError(f"Invalid processor version type: {type(v)}")

    @field_validator("data_classification")
    @classmethod
    def validate_data_classification(
        cls, v: Union[EnumDataClassification, str]
    ) -> EnumDataClassification:
        """Convert string data classification to enum."""
        if isinstance(v, EnumDataClassification):
            return v
        elif isinstance(v, str):
            try:
                return EnumDataClassification(v)
            except ValueError:
                # Try uppercase
                try:
                    return EnumDataClassification(v.upper())
                except ValueError:
                    raise ValueError(f"Invalid data classification: {v}")
        else:
            # This should never happen with proper typing, but handle gracefully
            raise ValueError(f"Invalid data classification type: {type(v)}")

    @field_validator("retention_policy")
    @classmethod
    def validate_retention_policy(
        cls, v: Union[EnumRetentionPolicy, str, None]
    ) -> EnumRetentionPolicy | None:
        """Convert string retention policy to enum."""
        if v is None:
            return None
        elif isinstance(v, EnumRetentionPolicy):
            return v
        elif isinstance(v, str):
            try:
                return EnumRetentionPolicy(v)
            except ValueError:
                # Try uppercase
                try:
                    return EnumRetentionPolicy(v.upper())
                except ValueError:
                    raise ValueError(f"Invalid retention policy: {v}")
        else:
            # This should never happen with proper typing, but handle gracefully
            raise ValueError(f"Invalid retention policy type: {type(v)}")

    @field_validator("custom_metadata")
    @classmethod
    def validate_custom_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate custom metadata values and store as raw Python types."""
        result = {}
        for key, value in v.items():
            if isinstance(value, ModelCliValue):
                # Extract raw value from ModelCliValue
                result[key] = value.to_python_value()
            else:
                # Validate by creating ModelCliValue but store raw value
                ModelCliValue.from_any(value)  # This validates the value
                result[key] = value
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
            raise ValueError("Quality score must be between 0.0 and 1.0")

    def set_confidence_level(self, confidence: float) -> None:
        """Set the confidence level."""
        if 0.0 <= confidence <= 1.0:
            self.confidence_level = confidence
        else:
            raise ValueError("Confidence level must be between 0.0 and 1.0")

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

    def set_custom_field(self, key: str, value: Any) -> None:
        """Set a custom metadata field with automatic type conversion."""
        # Validate the value by creating ModelCliValue but store raw value
        ModelCliValue.from_any(value)  # This validates the value
        self.custom_metadata[key] = value

    def get_custom_field(self, key: str, default: Any = None) -> Any:
        """Get a custom metadata field with original type."""
        return self.custom_metadata.get(key, default)

    def is_compliant(self) -> bool:
        """Check if all compliance flags are True."""
        return all(self.compliance_flags.values()) if self.compliance_flags else True

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "ModelCliResultMetadata":
        """Custom validation to handle 'labels' field."""
        if isinstance(obj, dict) and "labels" in obj:
            # Handle legacy 'labels' field by converting to label_ids/label_names
            labels = obj.pop("labels")
            if isinstance(labels, dict):
                label_ids = {}
                label_names = {}
                for key, value in labels.items():
                    uuid_id = uuid_from_string(key, "label")
                    label_ids[uuid_id] = value
                    label_names[key] = uuid_id
                obj["label_ids"] = label_ids
                obj["label_names"] = label_names

        return super().model_validate(
            obj,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": True,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelCliResultMetadata"]

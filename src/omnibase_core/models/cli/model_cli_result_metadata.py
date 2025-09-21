"""
CLI result metadata model.

Clean, strongly-typed replacement for dict[str, Any] in CLI result metadata.
Follows ONEX one-model-per-file naming conventions.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from ..metadata.model_semver import ModelSemVer


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
    result_type: str = Field(default="cli_result", description="Type of result")
    result_category: str | None = Field(None, description="Result category")

    # Source information
    source_command: str | None = Field(None, description="Source command")
    source_node: str | None = Field(None, description="Source node")

    # Processing metadata
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When result was processed",
    )
    processor_version: ModelSemVer | None = Field(None, description="Processor version")

    # Quality metrics
    quality_score: float | None = Field(
        None, description="Quality score (0.0 to 1.0)", ge=0.0, le=1.0
    )
    confidence_level: float | None = Field(
        None, description="Confidence level (0.0 to 1.0)", ge=0.0, le=1.0
    )

    # Data classification
    data_classification: str = Field(
        default="internal", description="Data classification level"
    )
    retention_policy: str | None = Field(None, description="Data retention policy")

    # Tags and labels
    tags: list[str] = Field(default_factory=list, description="Result tags")
    labels: dict[str, str] = Field(default_factory=dict, description="Key-value labels")

    # Performance metrics
    processing_time_ms: float | None = Field(
        None, description="Processing time in milliseconds"
    )
    resource_usage: dict[str, float] = Field(
        default_factory=dict, description="Resource usage metrics"
    )

    # Compliance and audit
    compliance_flags: dict[str, bool] = Field(
        default_factory=dict, description="Compliance flags"
    )
    audit_trail: list[str] = Field(
        default_factory=list, description="Audit trail entries"
    )

    # Custom metadata fields for extensibility
    custom_metadata: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Custom metadata fields"
    )

    def add_tag(self, tag: str) -> None:
        """Add a tag to the result."""
        if tag not in self.tags:
            self.tags.append(tag)

    def add_label(self, key: str, value: str) -> None:
        """Add a label to the result."""
        self.labels[key] = value

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

    def set_custom_field(self, key: str, value: str | int | bool | float) -> None:
        """Set a custom metadata field."""
        self.custom_metadata[key] = value

    def get_custom_field(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get a custom metadata field."""
        return self.custom_metadata.get(key, default)

    def is_compliant(self) -> bool:
        """Check if all compliance flags are True."""
        return all(self.compliance_flags.values()) if self.compliance_flags else True


# Export the model
__all__ = ["ModelCliResultMetadata"]

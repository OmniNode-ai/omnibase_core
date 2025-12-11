"""
Detection Configuration Model.

Overall configuration for sensitive information detection system.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.security.model_security_summaries import (
    ModelDetectionConfigSummary,
    ModelDetectionFeatures,
)


class ModelDetectionConfiguration(BaseModel):
    """
    Overall configuration for sensitive information detection system.
    """

    config_id: UUID = Field(description="Unique identifier for this configuration")
    config_name: str = Field(description="Human-readable name for this configuration")
    enabled_rulesets: list[str] = Field(
        default_factory=list,
        description="IDs of enabled rulesets",
    )
    global_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Global minimum confidence threshold",
    )
    max_document_size_mb: int = Field(
        default=10,
        ge=1,
        description="Maximum document size to process",
    )
    enable_false_positive_reduction: bool = Field(
        default=True,
        description="Whether to apply false positive reduction",
    )
    enable_context_analysis: bool = Field(
        default=True,
        description="Whether to use context analysis",
    )
    enable_ml_detection: bool = Field(
        default=True,
        description="Whether to use ML-based detection",
    )
    parallel_processing_workers: int = Field(
        default=4,
        ge=1,
        description="Number of parallel processing workers",
    )
    audit_logging_enabled: bool = Field(
        default=True,
        description="Whether to log all detections for audit",
    )
    redaction_character: str = Field(
        default="*",
        description="Character to use for redaction",
    )
    preserve_format: bool = Field(
        default=True,
        description="Whether to preserve original formatting in redacted text",
    )
    supported_file_types: list[str] = Field(
        default_factory=lambda: ["txt", "pdf", "docx", "html", "md"],
        description="Supported file types for processing",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    def is_ruleset_enabled(self, ruleset_id: UUID) -> bool:
        """Check if a ruleset is enabled."""
        return ruleset_id in self.enabled_rulesets

    def enable_ruleset(self, ruleset_id: UUID) -> "ModelDetectionConfiguration":
        """Enable a ruleset."""
        if ruleset_id not in self.enabled_rulesets:
            new_rulesets = [*self.enabled_rulesets, ruleset_id]
            return self.model_copy(update={"enabled_rulesets": new_rulesets})
        return self

    def disable_ruleset(self, ruleset_id: UUID) -> "ModelDetectionConfiguration":
        """Disable a ruleset."""
        new_rulesets = [r for r in self.enabled_rulesets if r != ruleset_id]
        return self.model_copy(update={"enabled_rulesets": new_rulesets})

    def supports_file_type(self, file_type: str) -> bool:
        """Check if file type is supported."""
        return file_type.lower() in [ft.lower() for ft in self.supported_file_types]

    def meets_confidence_threshold(self, confidence: float) -> bool:
        """Check if confidence meets global threshold."""
        return confidence >= self.global_confidence_threshold

    def get_summary(self) -> ModelDetectionConfigSummary:
        """Get configuration summary."""
        return ModelDetectionConfigSummary(
            config_id=self.config_id,
            config_name=self.config_name,
            enabled_rulesets_count=len(self.enabled_rulesets),
            global_confidence_threshold=self.global_confidence_threshold,
            max_document_size_mb=self.max_document_size_mb,
            parallel_workers=self.parallel_processing_workers,
            supported_file_types=self.supported_file_types,
            features=ModelDetectionFeatures(
                false_positive_reduction=self.enable_false_positive_reduction,
                context_analysis=self.enable_context_analysis,
                ml_detection=self.enable_ml_detection,
                audit_logging=self.audit_logging_enabled,
            ),
        )

"""
Sensitive information model for detection configurations and patterns.

Provides strongly-typed models for configuring sensitive information detection.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.security.model_detection_result import (
    EnumDetectionMethod,
    EnumDetectionType,
    EnumSensitivityLevel,
)


class EnumLanguageCode(str, Enum):
    """Supported language codes for detection."""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    SWEDISH = "sv"
    NORWEGIAN = "no"
    DANISH = "da"
    FINNISH = "fi"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"


class ModelDetectionPattern(BaseModel):
    """
    Configuration for a single detection pattern.
    """

    pattern_id: str = Field(description="Unique identifier for this pattern")

    pattern_name: str = Field(description="Human-readable name for this pattern")

    pattern_regex: str | None = Field(
        default=None,
        description="Regular expression pattern",
    )

    pattern_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords to match",
    )

    detection_type: EnumDetectionType = Field(
        description="Type of sensitive information this pattern detects",
    )

    sensitivity_level: EnumSensitivityLevel = Field(
        description="Sensitivity level for matches from this pattern",
    )

    detection_method: EnumDetectionMethod = Field(
        description="Primary detection method for this pattern",
    )

    confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for matches",
    )

    context_window_size: int = Field(
        default=50,
        ge=0,
        description="Size of context window around matches",
    )

    enabled: bool = Field(
        default=True,
        description="Whether this pattern is currently enabled",
    )

    languages: list[EnumLanguageCode] = Field(
        default_factory=lambda: [EnumLanguageCode.ENGLISH],
        description="Languages this pattern supports",
    )

    false_positive_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to exclude as false positives",
    )

    examples: list[str] = Field(
        default_factory=list,
        description="Example strings this pattern should match",
    )

    description: str | None = Field(
        default=None,
        description="Description of what this pattern detects",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )


class ModelDetectionRuleSet(BaseModel):
    """
    Collection of detection patterns organized by type.
    """

    ruleset_id: str = Field(description="Unique identifier for this ruleset")

    ruleset_name: str = Field(description="Human-readable name for this ruleset")

    version: str = Field(description="Version of this ruleset")

    patterns: list[ModelDetectionPattern] = Field(
        default_factory=list,
        description="Detection patterns in this ruleset",
    )

    detection_types: list[EnumDetectionType] = Field(
        default_factory=list,
        description="Types of detection covered by this ruleset",
    )

    supported_languages: list[EnumLanguageCode] = Field(
        default_factory=list,
        description="Languages supported by this ruleset",
    )

    performance_target_docs_per_minute: int | None = Field(
        default=None,
        description="Target processing speed for this ruleset",
    )

    memory_limit_mb: int | None = Field(
        default=None,
        description="Memory limit for processing with this ruleset",
    )

    created_date: str | None = Field(
        default=None,
        description="Creation date (ISO format)",
    )

    last_updated: str | None = Field(
        default=None,
        description="Last update date (ISO format)",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing this ruleset",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )


class ModelDetectionConfiguration(BaseModel):
    """
    Overall configuration for sensitive information detection system.
    """

    config_id: str = Field(description="Unique identifier for this configuration")

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

"""
ONEX Standards Injection Models for Enhanced Context System.

These models define the structure for automatic injection of ONEX coding standards
into Claude's context when code generation is detected.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EnumONEXStandardsSection(str, Enum):
    """Enumeration for ONEX standards sections."""

    # HIGHEST PRIORITY - Always injected for coding tasks
    HIGHEST_PRIORITY_CORE_PRINCIPLES = "highest_priority_core_principles"

    # Core standards
    CRITICAL_ENFORCEMENT_RULES = "critical_enforcement_rules"
    REQUIRED_EXECUTION_MODE = "required_execution_mode"
    OUTPUT_STANDARDS = "output_standards"
    PROTOCOL_RESOLUTION_RULES = "protocol_resolution_rules"
    TOOL_USAGE = "tool_usage"
    INFRA_NOTES = "infra_notes"
    DEBUG_INTELLIGENCE_DASHBOARD = "debug_intelligence_dashboard"


class EnumCodeDetectionConfidence(str, Enum):
    """Enumeration for code detection confidence levels."""

    HIGH = "high"  # > 0.8 - Definitely coding task
    MEDIUM = "medium"  # 0.6-0.8 - Likely coding task
    LOW = "low"  # 0.3-0.6 - Possibly coding task
    NONE = "none"  # < 0.3 - Not coding task


class ModelOnexStandardsSection(BaseModel):
    """Model for individual ONEX standards section."""

    section_type: EnumONEXStandardsSection = Field(
        ...,
        description="Type of standards section",
    )
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Priority level (1=highest, 5=lowest)",
    )
    token_estimate: int = Field(
        default=0,
        ge=0,
        description="Estimated token count for this section",
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score for current request",
    )


class ModelCodeDetectionAnalysis(BaseModel):
    """Model for code generation detection analysis."""

    user_request: str = Field(..., description="Original user request")
    coding_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence this is a coding task",
    )
    confidence_level: EnumCodeDetectionConfidence = Field(
        ...,
        description="Categorized confidence level",
    )

    # Detection factors
    keyword_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from coding keywords",
    )
    technical_context_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from technical context",
    )
    intent_category_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from intent categorization",
    )
    structure_analysis_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from request structure",
    )

    # Detected patterns
    detected_keywords: list[str] = Field(
        default_factory=list,
        description="Coding-related keywords found",
    )
    detected_technologies: list[str] = Field(
        default_factory=list,
        description="Technologies/frameworks detected",
    )
    detected_onex_terms: list[str] = Field(
        default_factory=list,
        description="ONEX-specific terms detected",
    )

    # Recommendations
    should_inject_standards: bool = Field(
        ...,
        description="Whether to inject ONEX standards",
    )
    recommended_sections: list[EnumONEXStandardsSection] = Field(
        default_factory=list,
        description="Recommended standards sections",
    )


class ModelOnexStandardsInjection(BaseModel):
    """Model for ONEX standards injection response."""

    injection_id: str = Field(..., description="Unique injection identifier")
    user_request: str = Field(..., description="Original user request")

    # Detection results
    code_detection: ModelCodeDetectionAnalysis = Field(
        ...,
        description="Code detection analysis results",
    )

    # Injected standards
    injected_sections: list[ModelOnexStandardsSection] = Field(
        default_factory=list,
        description="Standards sections injected",
    )
    standards_summary: str = Field(..., description="Summary of injected standards")

    # Context formatting
    formatted_standards: str = Field(
        ...,
        description="Formatted standards text for Claude context",
    )
    total_standards_tokens: int = Field(
        default=0,
        ge=0,
        description="Total token count for standards",
    )

    # Performance metrics
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Time taken to process standards injection",
    )
    cache_hit: bool = Field(
        default=False,
        description="Whether standards were loaded from cache",
    )

    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When injection was performed",
    )
    success: bool = Field(..., description="Whether standards injection succeeded")
    error_message: str | None = Field(
        None,
        description="Error message if injection failed",
    )


class ModelOnexStandardsSettings(BaseModel):
    """Model for ONEX standards injection settings."""

    enabled: bool = Field(
        default=True,
        description="Whether standards injection is enabled",
    )

    # Detection thresholds
    minimum_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to trigger standards injection",
    )
    full_standards_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for full standards injection",
    )

    # Content limits
    max_standards_tokens: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum tokens for standards content",
    )
    max_sections_per_injection: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum standards sections per injection",
    )

    # Section priorities
    section_priorities: dict[str, int] = Field(
        default_factory=lambda: {
            EnumONEXStandardsSection.CRITICAL_ENFORCEMENT_RULES.value: 1,
            EnumONEXStandardsSection.REQUIRED_EXECUTION_MODE.value: 2,
            EnumONEXStandardsSection.OUTPUT_STANDARDS.value: 2,
            EnumONEXStandardsSection.PROTOCOL_RESOLUTION_RULES.value: 3,
            EnumONEXStandardsSection.TOOL_USAGE.value: 3,
            EnumONEXStandardsSection.INFRA_NOTES.value: 4,
            EnumONEXStandardsSection.DEBUG_INTELLIGENCE_DASHBOARD.value: 5,
        },
        description="Priority mapping for standards sections",
    )

    # Performance settings
    cache_standards: bool = Field(
        default=True,
        description="Whether to cache parsed standards",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Standards cache TTL",
    )

    # Quality settings
    prioritize_critical_rules: bool = Field(
        default=True,
        description="Always prioritize critical enforcement rules",
    )
    context_aware_selection: bool = Field(
        default=True,
        description="Select sections based on request context",
    )
    token_budget_enforcement: bool = Field(
        default=True,
        description="Enforce token budget limits",
    )


class ModelOnexStandardsCache(BaseModel):
    """Model for caching parsed ONEX standards."""

    cache_key: str = Field(..., description="Unique cache key")
    parsed_sections: list[ModelOnexStandardsSection] = Field(
        ...,
        description="Parsed standards sections",
    )
    source_file_hash: str = Field(..., description="Hash of source CLAUDE.md file")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When cache was created",
    )
    expires_at: datetime = Field(..., description="When cache expires")
    access_count: int = Field(default=1, ge=1, description="Number of cache accesses")
    last_accessed: datetime = Field(
        default_factory=datetime.now,
        description="Last access timestamp",
    )


class ModelOnexStandardsMetrics(BaseModel):
    """Model for ONEX standards injection metrics."""

    total_requests: int = Field(
        default=0,
        ge=0,
        description="Total standards injection requests",
    )
    successful_injections: int = Field(
        default=0,
        ge=0,
        description="Successful standards injections",
    )
    failed_injections: int = Field(
        default=0,
        ge=0,
        description="Failed standards injections",
    )

    # Detection metrics
    code_detection_accuracy: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Code detection accuracy",
    )
    average_confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average detection confidence",
    )

    # Performance metrics
    average_processing_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Average processing time",
    )
    cache_hit_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Standards cache hit rate",
    )

    # Usage metrics
    requests_by_confidence: dict[str, int] = Field(
        default_factory=dict,
        description="Requests by confidence level",
    )
    most_injected_sections: dict[str, int] = Field(
        default_factory=dict,
        description="Most frequently injected sections",
    )

    # Timestamp
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="When metrics were last updated",
    )

"""
ONEX Standards YAML Configuration Models.

Pydantic models for parsing and validating the ONEX_STANDARDS.yaml file structure.
This enforces our own standards by using proper models instead of raw dict parsing.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelOnexStandardsMetadata(BaseModel):
    """Model for ONEX standards YAML metadata section."""

    version: str = Field(..., description="Version of the standards configuration")
    last_updated: str = Field(..., description="Last update date")
    description: str = Field(..., description="Description of the standards file")


class ModelOnexStandardsInjectionConfig(BaseModel):
    """Model for injection configuration rules."""

    always_inject: List[str] = Field(
        default_factory=list,
        description="Standards sections to always inject regardless of confidence",
    )
    high_confidence: List[str] = Field(
        default_factory=list,
        description="Standards sections to inject for high confidence (>0.8)",
    )
    medium_confidence: List[str] = Field(
        default_factory=list,
        description="Standards sections to inject for medium confidence (>0.6)",
    )
    on_demand: List[str] = Field(
        default_factory=list,
        description="Standards sections to inject only when specifically requested",
    )


class ModelOnexStandardsConfidenceThresholds(BaseModel):
    """Model for confidence threshold configuration."""

    high: float = Field(
        default=0.8, ge=0.0, le=1.0, description="High confidence threshold"
    )
    medium: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Medium confidence threshold"
    )
    low: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Low confidence threshold"
    )


class ModelOnexStandardsSectionData(BaseModel):
    """Model for individual standards section data from YAML."""

    priority: int = Field(
        ..., ge=1, le=10, description="Priority level (1=highest, 10=lowest)"
    )
    always_inject: Optional[bool] = Field(
        None, description="Whether this section should always be injected"
    )
    title: str = Field(..., description="Section title")
    description: str = Field(..., description="Section description")
    content: str = Field(..., description="Section content")
    violations_to_reject: Optional[List[str]] = Field(
        None, description="List of violations that must be rejected"
    )
    enforcement_actions: Optional[List[str]] = Field(
        None, description="Actions to take for enforcement"
    )
    examples: Optional[Dict[str, str]] = Field(
        None, description="Code examples (correct/incorrect)"
    )


class ModelOnexStandardsContextRules(BaseModel):
    """Model for context-specific injection rules."""

    file_patterns: Dict[str, List[str]] = Field(
        default_factory=dict, description="File patterns mapped to standards sections"
    )
    keyword_triggers: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Keywords that trigger specific standards sections",
    )


class ModelOnexStandardsFormatting(BaseModel):
    """Model for formatting preferences."""

    max_content_length: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum characters per injected section",
    )
    include_examples: bool = Field(
        default=True, description="Include code examples when available"
    )
    include_violations: bool = Field(
        default=True, description="Include common violations to avoid"
    )
    priority_ordering: bool = Field(
        default=True, description="Order sections by priority in context"
    )


class ModelOnexStandardsYamlConfig(BaseModel):
    """Model for the complete ONEX_STANDARDS.yaml configuration."""

    metadata: ModelOnexStandardsMetadata = Field(
        ..., description="Metadata about the standards configuration"
    )
    injection_config: ModelOnexStandardsInjectionConfig = Field(
        ..., description="Configuration for when to inject different standards"
    )
    confidence_thresholds: ModelOnexStandardsConfidenceThresholds = Field(
        ..., description="Confidence thresholds for different injection levels"
    )
    standards: Dict[str, ModelOnexStandardsSectionData] = Field(
        ..., description="Standards sections with their data"
    )
    context_rules: ModelOnexStandardsContextRules = Field(
        ..., description="Context-specific injection rules"
    )
    formatting: ModelOnexStandardsFormatting = Field(
        ..., description="Formatting preferences for injection"
    )

    class Config:
        """Pydantic config for YAML parsing."""

        extra = "forbid"  # Reject unknown fields to enforce schema compliance
        validate_assignment = True  # Validate on assignment

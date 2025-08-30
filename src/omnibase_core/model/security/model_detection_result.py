"""
Detection result model for sensitive information detection.

Provides strongly-typed results from sensitive information detection operations.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EnumSensitivityLevel(str, Enum):
    """Sensitivity levels for detected information."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EnumDetectionType(str, Enum):
    """Types of sensitive information detection."""

    PII = "pii"
    SECRET = "secret"
    PROPRIETARY = "proprietary"
    CREDENTIAL = "credential"
    API_KEY = "api_key"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    GOVERNMENT_ID = "government_id"
    CUSTOM = "custom"


class EnumDetectionMethod(str, Enum):
    """Methods used for detection."""

    REGEX = "regex"
    ML_MODEL = "ml_model"
    ENTROPY_ANALYSIS = "entropy_analysis"
    DICTIONARY_MATCH = "dictionary_match"
    CONTEXT_ANALYSIS = "context_analysis"
    HYBRID = "hybrid"


class ModelDetectionMatch(BaseModel):
    """
    A single detection match within content.
    """

    start_position: int = Field(description="Start character position of the match")

    end_position: int = Field(description="End character position of the match")

    matched_text: str = Field(description="The actual text that was detected")

    redacted_text: Optional[str] = Field(
        default=None, description="Redacted version of the matched text"
    )

    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence score for this detection (0-1)"
    )

    detection_type: EnumDetectionType = Field(
        description="Type of sensitive information detected"
    )

    sensitivity_level: EnumSensitivityLevel = Field(
        description="Sensitivity level of the detected information"
    )

    detection_method: EnumDetectionMethod = Field(
        description="Method used to detect this information"
    )

    pattern_name: Optional[str] = Field(
        default=None, description="Name of the pattern that matched"
    )

    context_before: Optional[str] = Field(
        default=None, description="Text context before the match"
    )

    context_after: Optional[str] = Field(
        default=None, description="Text context after the match"
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional detection metadata (string values only)",
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )


class ModelDetectionResult(BaseModel):
    """
    Complete result from sensitive information detection operation.
    """

    document_id: str = Field(description="Unique identifier for the analyzed document")

    total_matches: int = Field(
        default=0, description="Total number of sensitive matches found"
    )

    matches: List[ModelDetectionMatch] = Field(
        default_factory=list, description="List of all detection matches"
    )

    highest_sensitivity: Optional[EnumSensitivityLevel] = Field(
        default=None, description="Highest sensitivity level found in document"
    )

    detection_types_found: List[EnumDetectionType] = Field(
        default_factory=list, description="Types of sensitive information detected"
    )

    overall_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for all detections",
    )

    processing_time_ms: Optional[int] = Field(
        default=None, description="Time taken to process document in milliseconds"
    )

    document_length: Optional[int] = Field(
        default=None, description="Length of analyzed document in characters"
    )

    scan_coverage_percentage: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Percentage of document scanned"
    )

    false_positive_reduction_applied: bool = Field(
        default=False, description="Whether false positive reduction was applied"
    )

    detection_methods_used: List[EnumDetectionMethod] = Field(
        default_factory=list, description="Detection methods used in analysis"
    )

    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for handling detected information",
    )

    audit_trail_id: Optional[str] = Field(
        default=None, description="ID for audit trail record"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )

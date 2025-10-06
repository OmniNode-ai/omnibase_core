from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field


class ModelDetectionResult(BaseModel):
    """
    Complete result from sensitive information detection operation.
    """

    document_id: str = Field(description="Unique identifier for the analyzed document")

    total_matches: int = Field(
        default=0,
        description="Total number of sensitive matches found",
    )

    matches: list[ModelDetectionMatch] = Field(
        default_factory=list,
        description="List of all detection matches",
    )

    highest_sensitivity: EnumSensitivityLevel | None = Field(
        default=None,
        description="Highest sensitivity level found in document",
    )

    detection_types_found: list[EnumDetectionType] = Field(
        default_factory=list,
        description="Types of sensitive information detected",
    )

    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for all detections",
    )

    processing_time_ms: int | None = Field(
        default=None,
        description="Time taken to process document in milliseconds",
    )

    document_length: int | None = Field(
        default=None,
        description="Length of analyzed document in characters",
    )

    scan_coverage_percentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Percentage of document scanned",
    )

    false_positive_reduction_applied: bool = Field(
        default=False,
        description="Whether false positive reduction was applied",
    )

    detection_methods_used: list[EnumDetectionMethod] = Field(
        default_factory=list,
        description="Detection methods used in analysis",
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for handling detected information",
    )

    audit_trail_id: str | None = Field(
        default=None,
        description="ID for audit trail record",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

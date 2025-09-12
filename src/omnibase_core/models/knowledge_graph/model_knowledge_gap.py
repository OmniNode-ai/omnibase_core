"""
Knowledge gap model for identifying missing documentation or relationships.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EnumGapType(str, Enum):
    """Types of knowledge gaps."""

    MISSING_DOCUMENTATION = "missing_documentation"
    MISSING_RELATIONSHIP = "missing_relationship"
    OUTDATED_INFORMATION = "outdated_information"
    INCOMPLETE_COVERAGE = "incomplete_coverage"
    BROKEN_REFERENCE = "broken_reference"
    ORPHANED_ENTITY = "orphaned_entity"
    SEMANTIC_INCONSISTENCY = "semantic_inconsistency"


class ModelKnowledgeGap(BaseModel):
    """Model for identified knowledge gaps."""

    gap_id: str = Field(..., description="Unique identifier for the gap")
    gap_type: EnumGapType = Field(..., description="Type of knowledge gap")
    severity: str = Field(
        ...,
        description="Severity level (low, medium, high, critical)",
    )
    description: str = Field(..., description="Description of the gap")

    # Location information
    affected_entity_ids: list[str] = Field(
        default_factory=list,
        description="Entities affected by this gap",
    )
    source_locations: list[str] = Field(
        default_factory=list,
        description="File paths where gap was detected",
    )

    # Analysis metadata
    confidence_score: float = Field(
        ...,
        description="Confidence in gap detection (0.0-1.0)",
    )
    detection_method: str = Field(..., description="Method used to detect the gap")
    suggested_action: str = Field(..., description="Recommended action to address gap")

    # Priority information
    impact_score: float = Field(..., description="Impact assessment (0.0-1.0)")
    urgency_score: float = Field(..., description="Urgency assessment (0.0-1.0)")
    priority_rank: int = Field(0, description="Overall priority ranking")

    # Temporal tracking
    detected_at: datetime = Field(
        default_factory=datetime.now,
        description="When gap was detected",
    )
    last_validated: datetime | None = Field(
        None,
        description="When gap was last validated",
    )
    resolved_at: datetime | None = Field(None, description="When gap was resolved")

    # Resolution tracking
    resolution_status: str = Field("open", description="Resolution status")
    resolution_notes: str | None = Field(None, description="Notes about resolution")

    model_config = ConfigDict(frozen=False, validate_assignment=True)

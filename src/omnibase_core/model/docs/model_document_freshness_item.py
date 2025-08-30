"""
Document Freshness Item Model

Individual document freshness analysis result.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_document_freshness_actions import \
    EnumDocumentFreshnessRiskLevel


class ModelDocumentFreshnessItem(BaseModel):
    """Individual document freshness analysis result."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    file_path: str = Field(description="Path to the document")
    freshness_score: float = Field(
        ge=0.0, le=1.0, description="Freshness score (0=stale, 1=fresh)"
    )
    last_modified: datetime = Field(description="Last modification timestamp")
    staleness_days: int = Field(
        ge=0, description="Number of days since last modification"
    )
    risk_level: EnumDocumentFreshnessRiskLevel = Field(
        description="Risk level based on staleness"
    )
    git_last_commit: Optional[datetime] = Field(
        default=None, description="Last Git commit timestamp for this file"
    )
    dependency_count: int = Field(
        default=0, ge=0, description="Number of dependencies identified"
    )

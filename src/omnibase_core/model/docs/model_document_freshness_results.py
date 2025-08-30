"""
Document Freshness Results Model

Complete freshness monitoring results.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_document_freshness_actions import \
    EnumDocumentFreshnessStatus
from omnibase_core.model.docs.model_document_freshness_item import \
    ModelDocumentFreshnessItem
from omnibase_core.model.docs.model_freshness_summary import \
    ModelFreshnessSummary


class ModelDocumentFreshnessResults(BaseModel):
    """Complete freshness monitoring results."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    documents: List[ModelDocumentFreshnessItem] = Field(
        description="Detailed freshness analysis for each document"
    )
    summary: ModelFreshnessSummary = Field(description="Summary statistics")
    overall_status: EnumDocumentFreshnessStatus = Field(
        description="Overall freshness status"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the analysis was performed"
    )

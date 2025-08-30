"""
Audit Report Model

Comprehensive audit report combining all analyses.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.docs.model_change_detection_results import \
    ModelChangeDetectionResults
from omnibase_core.model.docs.model_dependency_analysis_results import \
    ModelDependencyAnalysisResults
from omnibase_core.model.docs.model_document_freshness_results import \
    ModelDocumentFreshnessResults
from omnibase_core.model.docs.model_recommendation import ModelRecommendation


class ModelAuditReport(BaseModel):
    """Comprehensive audit report combining all analyses."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    report_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the report was generated"
    )
    target_paths: List[str] = Field(description="Paths that were analyzed")
    freshness_analysis: ModelDocumentFreshnessResults = Field(
        description="Document freshness analysis results"
    )
    dependency_analysis: ModelDependencyAnalysisResults = Field(
        description="Dependency analysis results"
    )
    change_analysis: ModelChangeDetectionResults = Field(
        description="Change detection analysis results"
    )
    recommendations: List[ModelRecommendation] = Field(
        description="Recommendations for improvements"
    )

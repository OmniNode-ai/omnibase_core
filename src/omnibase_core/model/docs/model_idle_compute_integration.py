"""
Models for document freshness idle compute integration.

ONEX-compliant models for standardized data structures used in the
idle compute integration for document freshness monitoring.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_analysis_status import EnumAnalysisStatus


class ModelRegistryStatus(BaseModel):
    """Standardized registry status information."""

    is_running: bool
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    queue_depth: int


class ModelMonitoringConfig(BaseModel):
    """Standardized monitoring configuration."""

    scan_interval_hours: int
    priority_refresh_hours: int
    batch_size: int
    max_concurrent_analysis: int


class ModelFreshnessAnalysis(BaseModel):
    """Standardized freshness analysis results."""

    status: str
    score: float
    stale_dependencies: int
    critical_dependencies: int


class ModelImpactAnalysis(BaseModel):
    """Standardized impact analysis results."""

    requires_update: bool
    update_priority: str
    coverage_score: float
    confidence_score: float
    suggested_actions: List[str]


class ModelDependencyAnalysis(BaseModel):
    """Standardized dependency analysis results."""

    graph_id: Optional[str] = None
    total_dependencies: int
    critical_dependencies: int
    stale_dependencies: int
    missing_dependencies: int
    impact_analysis: Optional["ModelImpactAnalysis"] = None
    error: Optional[str] = None


class ModelQualityAnalysis(BaseModel):
    """Standardized quality analysis results."""

    overall_score: float
    readability_score: float
    completeness_score: float
    accuracy_score: float
    structure_score: float
    issues_found: List[str]
    error: Optional[str] = None


class ModelCompletenessAnalysis(BaseModel):
    """Standardized completeness analysis results."""

    is_complete: bool
    missing_sections: List[str]
    coverage_percentage: float
    suggestions: List[str]


class ModelResourceUsage(BaseModel):
    """Standardized resource usage metrics."""

    cpu_percent_avg: float
    memory_mb_peak: float
    duration_seconds: float


class ModelTaskExecutionResult(BaseModel):
    """Standardized task execution result."""

    success: bool
    execution_time_seconds: float
    resource_usage: Optional["ModelResourceUsage"] = None
    error_message: Optional[str] = None
    output_summary: Optional[str] = None


class ModelTaskResult(BaseModel):
    """Model for task execution results."""

    document_path: str
    completion_time: str
    result: ModelTaskExecutionResult
    status: str


class ModelAnalysisStatus(BaseModel):
    """Model for analysis status response."""

    integration_id: str
    is_running: bool
    registered_documents: int
    completed_analyses: int
    target_directories: List[str] = Field(default_factory=list)
    registry_status: ModelRegistryStatus
    recent_completions: List[str] = Field(default_factory=list)
    monitoring_config: ModelMonitoringConfig


class ModelAnalysisResult(BaseModel):
    """Model for document analysis results."""

    document_path: str
    analysis_type: str
    started_at: str
    freshness_analysis: Optional[ModelFreshnessAnalysis] = None
    dependency_analysis: Optional[ModelDependencyAnalysis] = None
    ai_quality_analysis: Optional[ModelQualityAnalysis] = None
    quality_analysis: Optional[ModelQualityAnalysis] = None
    improvement_suggestions: Optional[List[str]] = None
    completeness_analysis: Optional[ModelCompletenessAnalysis] = None
    completed_at: Optional[str] = None
    status: str = EnumAnalysisStatus.PENDING
    error: Optional[str] = None
    summary: Optional[str] = None


# Rebuild models to resolve forward references
ModelDependencyAnalysis.model_rebuild()
ModelTaskExecutionResult.model_rebuild()

"""
Performance Report Models

ONEX-compliant models for performance reporting with strong typing.
"""

from typing import List

from pydantic import BaseModel


class ModelExecutorOverview(BaseModel):
    """Executor overview metrics."""

    executor_id: str
    uptime_seconds: float
    is_running: bool


class ModelExecutionStatistics(BaseModel):
    """Execution statistics."""

    total_tasks_executed: int
    total_tasks_failed: int
    total_execution_time_seconds: float
    average_execution_time_seconds: float
    resource_efficiency_scores: List[float]
    error_count: int
    preemption_count: int
    retry_count: int


class ModelCurrentLoad(BaseModel):
    """Current system load metrics."""

    active_tasks: int
    max_concurrent: int
    utilization_percent: float


class ModelResourceEfficiency(BaseModel):
    """Resource efficiency metrics."""

    average_efficiency_score: float
    recent_samples: int


class ModelErrorAnalysis(BaseModel):
    """Error analysis metrics."""

    total_errors: int
    error_rate: float
    retry_success_rate: float


class ModelConfiguration(BaseModel):
    """Configuration settings."""

    max_concurrent_tasks: int
    process_isolation: bool
    resource_monitoring: bool
    throttling_enabled: bool


class ModelPerformanceReport(BaseModel):
    """Complete performance report with strong typing."""

    executor_overview: ModelExecutorOverview
    execution_statistics: ModelExecutionStatistics
    current_load: ModelCurrentLoad
    resource_efficiency: ModelResourceEfficiency
    error_analysis: ModelErrorAnalysis
    configuration: ModelConfiguration

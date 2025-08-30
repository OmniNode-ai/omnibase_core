"""
Model for dashboard metrics data in the metrics collector service.

This model defines the structure for comprehensive metrics dashboard data.
"""

from pydantic import BaseModel


class ModelEventMetrics(BaseModel):
    """Metrics for a specific event."""

    count: int
    avg_duration: float


class ModelAgentPerformance(BaseModel):
    """Performance metrics for an agent."""

    total: int
    successful: int


class ModelKPI(BaseModel):
    """Key performance indicators."""

    total_throughput: float
    avg_throughput: float
    avg_error_rate: float
    max_error_rate: float


class ModelDashboardMetrics(BaseModel):
    """Comprehensive dashboard metrics data."""

    system_metrics: dict[str, float]
    agent_count: int
    health_score: float
    timestamp: str
    agent_summaries: dict[str, dict[str, float]]
    recent_events: dict[str, ModelEventMetrics]
    kpis: ModelKPI

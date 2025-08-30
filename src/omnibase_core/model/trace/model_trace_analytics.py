"""
Model for trace analytics in the traceability service.

This model defines the structure for comprehensive trace analytics data.
"""

from typing import Dict, List

from pydantic import BaseModel


class ModelAgentTracePerformance(BaseModel):
    """Performance metrics for an agent's traces."""

    total: int
    successful: int


class ModelComponentMetrics(BaseModel):
    """Metrics for a specific component."""

    component: str
    event_count: int


class ModelErrorMetrics(BaseModel):
    """Metrics for error patterns."""

    error: str
    count: int


class ModelTraceAnalytics(BaseModel):
    """Comprehensive trace analytics data."""

    total_traces: int
    active_traces: int
    completed_traces: int
    successful_traces: int
    failed_traces: int
    success_rate: float
    average_duration_ms: float
    total_events: int
    knowledge_contributions: int
    recent_activity_24h: int
    agent_performance: Dict[str, ModelAgentTracePerformance]
    top_components: List[ModelComponentMetrics]
    common_errors: List[ModelErrorMetrics]

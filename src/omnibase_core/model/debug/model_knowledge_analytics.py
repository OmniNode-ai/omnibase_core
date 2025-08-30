"""
Model for knowledge base analytics in the debug knowledge base service.

This model defines the structure for analytics data about the knowledge base.
"""

from pydantic import BaseModel


class ModelKnowledgeAnalytics(BaseModel):
    """Analytics data for the knowledge base."""

    total_entries: int
    successful_entries: int
    success_rate: float
    total_success_patterns: int
    total_failure_patterns: int
    total_insights: int
    unique_agents: int
    categories_covered: int
    recent_entries_7d: int
    knowledge_growth_rate: float
    database_status: str
    cache_size: int

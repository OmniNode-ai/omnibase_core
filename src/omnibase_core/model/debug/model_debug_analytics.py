"""
Model for debug analytics in the debug knowledge base service.

This model defines the structure for analytics data about the debug knowledge base.
"""

from typing import Set

from pydantic import BaseModel, Field

from omnibase_core.model.debug.model_agent_debug_entry import DebugCategory


class ModelDebugAnalytics(BaseModel):
    """Analytics data for the debug knowledge base."""

    total_entries: int = 0
    total_success_patterns: int = 0
    total_failure_patterns: int = 0
    total_insights: int = 0
    agents_contributing: Set[str] = Field(default_factory=set)
    categories_covered: Set[DebugCategory] = Field(default_factory=set)
    knowledge_growth_rate: float = 0.0

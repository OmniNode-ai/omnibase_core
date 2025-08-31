"""
Model for search filters in the debug knowledge base service.

This model defines the structure for search filters used to query debug entries.
"""

from pydantic import BaseModel

from omnibase_core.model.debug.model_agent_debug_entry import (
    DebugCategory,
    DebugSeverity,
)


class ModelSearchFilters(BaseModel):
    """Filters for searching debug entries."""

    agent_id: str | None = None
    category: DebugCategory | None = None
    success: bool | None = None
    severity: DebugSeverity | None = None

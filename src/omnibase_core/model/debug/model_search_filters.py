"""
Model for search filters in the debug knowledge base service.

This model defines the structure for search filters used to query debug entries.
"""

from typing import Optional

from pydantic import BaseModel

from omnibase_core.model.debug.model_agent_debug_entry import (DebugCategory,
                                                               DebugSeverity)


class ModelSearchFilters(BaseModel):
    """Filters for searching debug entries."""

    agent_id: Optional[str] = None
    category: Optional[DebugCategory] = None
    success: Optional[bool] = None
    severity: Optional[DebugSeverity] = None

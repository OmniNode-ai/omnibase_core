"""
Model for trace search filters in the traceability service.

This model defines the structure for filters used to search traces.
"""

from typing import Optional

from pydantic import BaseModel


class ModelTraceSearchFilters(BaseModel):
    """Filters for searching traces."""

    agent_id: Optional[str] = None
    success: Optional[bool] = None
    status: Optional[str] = None  # TraceStatus enum value

"""
Model for trace search filters in the traceability service.

This model defines the structure for filters used to search traces.
"""

from pydantic import BaseModel


class ModelTraceSearchFilters(BaseModel):
    """Filters for searching traces."""

    agent_id: str | None = None
    success: bool | None = None
    status: str | None = None  # TraceStatus enum value

"""
Model for trace event data in the traceability service.

This model defines the structure for data contained within trace events.
"""

from pydantic import BaseModel


class ModelTraceEventData(BaseModel):
    """Data structure for trace event data."""

    # Common fields
    task_id: str | None = None
    task_description: str | None = None
    agent_id: str | None = None
    component: str | None = None
    success: bool | None = None
    error_message: str | None = None

    # Performance metrics
    duration_ms: float | None = None
    total_duration_ms: float | None = None
    event_count: int | None = None

    # Additional context
    debug_entry_id: str | None = None
    metadata: dict[str, str] | None = None

    # For flexibility with different event types
    additional_data: dict[str, str] | None = None

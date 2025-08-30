"""
Model for trace event data in the traceability service.

This model defines the structure for data contained within trace events.
"""

from typing import Dict, Optional

from pydantic import BaseModel


class ModelTraceEventData(BaseModel):
    """Data structure for trace event data."""

    # Common fields
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    agent_id: Optional[str] = None
    component: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None

    # Performance metrics
    duration_ms: Optional[float] = None
    total_duration_ms: Optional[float] = None
    event_count: Optional[int] = None

    # Additional context
    debug_entry_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    # For flexibility with different event types
    additional_data: Optional[Dict[str, str]] = None

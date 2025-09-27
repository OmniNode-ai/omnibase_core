"""
Trace Data Model.

Restrictive model for CLI execution trace data
with proper typing and validation.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceData(BaseModel):
    """Restrictive model for trace data."""

    trace_id: UUID = Field(description="Unique trace identifier")
    span_id: UUID = Field(description="Span identifier")
    parent_span_id: UUID | None = Field(None, description="Parent span identifier")
    start_time: datetime = Field(description="Start timestamp")
    end_time: datetime = Field(description="End timestamp")
    duration_ms: float = Field(description="Duration in milliseconds")
    tags: dict[str, str] = Field(default_factory=dict, description="Trace tags")
    logs: list[str] = Field(default_factory=list, description="Trace log entries")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

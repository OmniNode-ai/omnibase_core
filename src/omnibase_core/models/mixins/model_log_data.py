"""
Log data model for structured logging in event bus operations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelLogData(BaseModel):
    """Log data model for structured logging in event bus operations."""

    model_config = ConfigDict(
        extra="forbid",  # Catch typos early
        frozen=True,  # Immutable instances for safer passing
        from_attributes=True,  # pytest-xdist compatibility
    )

    error: str | None = None
    pattern: str | None = None
    event_type: str | None = None
    node_name: str | None = None

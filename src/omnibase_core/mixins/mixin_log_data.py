from __future__ import annotations

"""
Log data model for structured logging in event bus operations.
"""


from pydantic import BaseModel


class MixinLogData(BaseModel):
    """Log data model for structured logging in event bus operations."""

    error: str | None = None
    pattern: str | None = None
    event_type: str | None = None
    node_name: str | None = None

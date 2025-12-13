"""
Tool Timeout Settings Model.

Timeout configuration for tools.
"""

from pydantic import BaseModel, Field


class ModelToolTimeoutSettings(BaseModel):
    """Timeout settings for a tool."""

    shutdown_timeout: int = Field(description="Graceful shutdown timeout in seconds")
    initialization_order: int = Field(
        description="Initialization order relative to other tools"
    )

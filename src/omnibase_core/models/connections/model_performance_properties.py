"""
Performance connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPerformanceProperties(BaseModel):
    """Performance tuning connection properties."""

    # All performance settings are numeric, not string
    max_connections: int | None = Field(default=None, description="Maximum connections")
    connection_limit: int | None = Field(default=None, description="Connection limit")
    command_timeout: int | None = Field(default=None, description="Command timeout")

    # Compression and optimization settings
    enable_compression: bool | None = Field(
        default=None,
        description="Enable compression",
    )
    compression_level: int | None = Field(default=None, description="Compression level")
    enable_caching: bool | None = Field(default=None, description="Enable caching")


# Export the model
__all__ = ["ModelPerformanceProperties"]
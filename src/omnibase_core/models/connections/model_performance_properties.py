"""
Performance connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPerformanceProperties(BaseModel):
    """Performance tuning connection properties."""

    # All performance settings are numeric, not string
    max_connections: int = Field(default=100, description="Maximum connections")
    connection_limit: int = Field(default=50, description="Connection limit")
    command_timeout: int = Field(default=30, description="Command timeout")

    # Compression and optimization settings
    enable_compression: bool = Field(
        default=False,
        description="Enable compression",
    )
    compression_level: int = Field(default=6, description="Compression level")
    enable_caching: bool = Field(default=True, description="Enable caching")


# Export the model
__all__ = ["ModelPerformanceProperties"]

"""
ModelAPIConfig

API server configuration for REST interface.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from pydantic import BaseModel, Field


class ModelAPIConfig(BaseModel):
    """API server configuration for REST interface."""

    host: str = Field(default="localhost", description="API host")
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=4, description="Number of workers")
    reload: bool = Field(default=False, description="Enable auto-reload")

    # Security
    api_key: str | None = Field(
        default=None,
        description="API key for authentication",
    )
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")

    # Performance
    max_concurrent_requests: int = Field(
        default=100,
        description="Max concurrent requests",
    )
    request_timeout: int = Field(default=300, description="Request timeout seconds")

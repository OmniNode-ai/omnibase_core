"""
ModelDatabaseConfig

Database configuration for persistent storage.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from pydantic import BaseModel, Field


class ModelDatabaseConfig(BaseModel):
    """Database configuration for persistent storage."""

    url: str = Field(default="postgresql://localhost/onex", description="Database URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout seconds")

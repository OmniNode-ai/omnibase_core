from typing import Generic

from pydantic import Field

"""
Model for generic connection configuration.

This model serves as a fallback for unknown service types,
providing a flexible but still typed structure.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_generic_connection_config_config import (
    ModelConfig,
)


class ModelGenericConnectionConfig(BaseModel):
    """Generic connection configuration for unknown service types."""

    host: str | None = Field(default=None, description="Service host")
    port: int | None = Field(default=None, description="Service port")
    url: str | None = Field(default=None, description="Connection URL")
    auth_type: str | None = Field(default=None, description="Authentication type")
    credentials: dict[str, str] | None = Field(
        default=None,
        description="Authentication credentials",
    )
    options: dict[str, str] | None = Field(
        default=None,
        description="Additional connection options",
    )
    timeout_seconds: int | None = Field(
        default=30,
        description="Connection timeout in seconds",
    )

    Config = ModelConfig  # Use the imported Config class

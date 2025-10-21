"""
Storage Configuration Model - ONEX Standards Compliant.

Strongly-typed model for storage backend configuration.
"""

from typing import Any

from pydantic import BaseModel, Field

from .model_storage_configuration_config import ModelConfig


class ModelStorageConfiguration(BaseModel):
    """
    Model for storage backend configuration.

    Used to configure storage backends with connection parameters,
    retention policies, and backend-specific settings.
    """

    backend_type: str = Field(description="Storage backend type")

    connection_params: dict[str, str] = Field(
        description="Backend connection parameters", default_factory=dict
    )

    retention_hours: int = Field(
        description="Checkpoint retention period in hours", default=72
    )

    max_checkpoint_size_mb: int = Field(
        description="Maximum checkpoint size in MB", default=100
    )

    enable_compression: bool = Field(
        description="Enable checkpoint data compression", default=True
    )

    enable_encryption: bool = Field(
        description="Enable checkpoint data encryption", default=False
    )

    backup_enabled: bool = Field(description="Enable automatic backups", default=False)

    health_check_interval_seconds: int = Field(
        description="Health check interval in seconds", default=60
    )

    additional_config: dict[str, Any] = Field(
        description="Backend-specific additional configuration", default_factory=dict
    )

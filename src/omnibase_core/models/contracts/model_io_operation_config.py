"""
I/O Operation Configuration Model.

Defines configuration for file operations, database interactions,
API calls, and other external I/O operations.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelIOOperationConfig(BaseModel):
    """
    I/O operation specifications.

    Defines configuration for file operations, database interactions,
    API calls, and other external I/O operations.
    """

    operation_type: str = Field(
        default=...,
        description="Type of I/O operation (file_read, file_write, db_query, api_call, etc.)",
        min_length=1,
    )

    atomic: bool = Field(default=True, description="Whether operation should be atomic")

    backup_enabled: bool = Field(
        default=False,
        description="Enable backup before destructive operations",
    )

    permissions: str | None = Field(
        default=None,
        description="File permissions or access rights",
    )

    recursive: bool = Field(
        default=False,
        description="Enable recursive operations for directories",
    )

    buffer_size: int = Field(
        default=8192,
        description="Buffer size for streaming operations",
        ge=1024,
    )

    timeout_seconds: int = Field(
        default=30,
        description="Operation timeout in seconds",
        ge=1,
    )

    validation_enabled: bool = Field(
        default=True,
        description="Enable operation result validation",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelIOOperationConfig"]

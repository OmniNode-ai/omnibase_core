#!/usr/bin/env python3
"""
Storage Result Models - ONEX Standards Compliant.

Strongly-typed models for storage backend operation results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_checkpoint_data import ModelCheckpointData


class ModelStorageResult(BaseModel):
    """
    Model for storage backend operation results.

    Used by storage backends to return standardized operation
    results with success/failure information and data payloads.
    """

    success: bool = Field(description="Whether the operation succeeded")

    checkpoint_data: Optional[ModelCheckpointData] = Field(
        description="Checkpoint data (for retrieval operations)",
        default=None,
    )

    operation_type: str = Field(description="Type of storage operation")

    error_message: Optional[str] = Field(
        description="Error message if operation failed",
        default=None,
    )

    metadata: Dict[str, Any] = Field(
        description="Operation metadata",
        default_factory=dict,
    )

    execution_time_ms: int = Field(
        description="Operation execution time in milliseconds",
        default=0,
    )

    affected_count: int = Field(
        description="Number of items affected by operation",
        default=0,
    )

    timestamp: datetime = Field(
        description="When the operation completed",
        default_factory=datetime.now,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModelStorageListResult(BaseModel):
    """
    Model for storage backend list operation results.

    Used by storage backends to return paginated lists of
    checkpoints with metadata and pagination information.
    """

    success: bool = Field(description="Whether the list operation succeeded")

    checkpoints: List[ModelCheckpointData] = Field(
        description="List of checkpoints",
        default_factory=list,
    )

    total_count: int = Field(
        description="Total number of available checkpoints",
        default=0,
    )

    returned_count: int = Field(
        description="Number of checkpoints in this result",
        default=0,
    )

    offset: int = Field(
        description="Offset used for this query",
        default=0,
    )

    limit: int = Field(
        description="Limit used for this query",
        default=0,
    )

    error_message: Optional[str] = Field(
        description="Error message if operation failed",
        default=None,
    )

    execution_time_ms: int = Field(
        description="List operation execution time in milliseconds",
        default=0,
    )

    timestamp: datetime = Field(
        description="When the list operation completed",
        default_factory=datetime.now,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModelStorageConfiguration(BaseModel):
    """
    Model for storage backend configuration.

    Used to configure storage backends with connection parameters,
    retention policies, and backend-specific settings.
    """

    backend_type: str = Field(description="Storage backend type")

    connection_params: Dict[str, str] = Field(
        description="Backend connection parameters",
        default_factory=dict,
    )

    retention_hours: int = Field(
        description="Checkpoint retention period in hours",
        default=72,
    )

    max_checkpoint_size_mb: int = Field(
        description="Maximum checkpoint size in MB",
        default=100,
    )

    enable_compression: bool = Field(
        description="Enable checkpoint data compression",
        default=True,
    )

    enable_encryption: bool = Field(
        description="Enable checkpoint data encryption",
        default=False,
    )

    backup_enabled: bool = Field(
        description="Enable automatic backups",
        default=False,
    )

    health_check_interval_seconds: int = Field(
        description="Health check interval in seconds",
        default=60,
    )

    additional_config: Dict[str, Any] = Field(
        description="Backend-specific additional configuration",
        default_factory=dict,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True


class ModelStorageHealthStatus(BaseModel):
    """
    Model for storage backend health status.

    Used by storage backends to report their operational
    status, capacity, and performance metrics.
    """

    backend_id: str = Field(description="Unique backend identifier")

    backend_type: str = Field(description="Storage backend type")

    is_healthy: bool = Field(description="Whether backend is healthy")

    is_connected: bool = Field(description="Whether backend is connected")

    total_capacity_mb: Optional[int] = Field(
        description="Total storage capacity in MB",
        default=None,
    )

    used_capacity_mb: Optional[int] = Field(
        description="Used storage capacity in MB",
        default=None,
    )

    available_capacity_mb: Optional[int] = Field(
        description="Available storage capacity in MB",
        default=None,
    )

    checkpoint_count: int = Field(
        description="Number of stored checkpoints",
        default=0,
    )

    last_health_check: datetime = Field(
        description="When health was last checked",
        default_factory=datetime.now,
    )

    average_response_time_ms: Optional[int] = Field(
        description="Average response time in milliseconds",
        default=None,
    )

    error_rate_percent: float = Field(
        description="Error rate percentage",
        default=0.0,
    )

    status_message: Optional[str] = Field(
        description="Detailed status message",
        default=None,
    )

    metadata: Dict[str, str] = Field(
        description="Additional health metadata",
        default_factory=dict,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}

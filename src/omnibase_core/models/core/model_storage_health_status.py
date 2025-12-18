from uuid import UUID

"""
Storage Health Status Model.

Strongly-typed model for storage backend health status.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelStorageHealthStatus(BaseModel):
    """
    Model for storage backend health status.

    Used by storage backends to report their operational
    status, capacity, and performance metrics.
    """

    backend_id: UUID = Field(description="Unique backend identifier")

    backend_type: str = Field(description="Storage backend type")

    is_healthy: bool = Field(description="Whether backend is healthy")

    is_connected: bool = Field(description="Whether backend is connected")

    total_capacity_mb: int | None = Field(
        description="Total storage capacity in MB", default=None
    )

    used_capacity_mb: int | None = Field(
        description="Used storage capacity in MB", default=None
    )

    available_capacity_mb: int | None = Field(
        description="Available storage capacity in MB", default=None
    )

    checkpoint_count: int = Field(description="Number of stored checkpoints", default=0)

    last_health_check: datetime = Field(
        description="When health was last checked", default_factory=datetime.now
    )

    average_response_time_ms: int | None = Field(
        description="Average response time in milliseconds", default=None
    )

    error_rate_percent: float = Field(description="Error rate percentage", default=0.0)

    status_message: str | None = Field(
        description="Detailed status message", default=None
    )

    metadata: dict[str, str] = Field(
        description="Additional health metadata", default_factory=dict
    )

"""
Model for Docker restart policy configuration.
"""

from pydantic import BaseModel, Field


class ModelDockerRestartPolicy(BaseModel):
    """Docker restart policy configuration."""

    name: str = Field(
        default="on-failure",
        description="Restart policy name: no, always, on-failure, unless-stopped",
    )
    maximum_retry_count: int | None = Field(
        default=None,
        description="Maximum retry count for on-failure policy",
    )
    window: int | None = Field(
        default=None,
        description="Window in seconds to wait before restarting",
    )

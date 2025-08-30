"""
Model for Docker restart policy configuration.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelDockerRestartPolicy(BaseModel):
    """Docker restart policy configuration."""

    name: str = Field(
        default="on-failure",
        description="Restart policy name: no, always, on-failure, unless-stopped",
    )
    maximum_retry_count: Optional[int] = Field(
        default=None, description="Maximum retry count for on-failure policy"
    )
    window: Optional[int] = Field(
        default=None, description="Window in seconds to wait before restarting"
    )

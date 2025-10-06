from pydantic import Field

"""
Request retry configuration model.
"""

from pydantic import BaseModel, Field


class ModelRequestRetryConfig(BaseModel):
    """Request retry configuration."""

    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, description="Initial retry delay in seconds")
    retry_backoff: float = Field(2.0, description="Exponential backoff factor")
    retry_on_status: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes to retry on",
    )

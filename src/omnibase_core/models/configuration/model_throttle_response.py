"""
ModelThrottleResponse - Typed response for throttled requests.

This model defines the structure for HTTP responses returned when requests
are throttled due to rate limiting.
"""

from pydantic import BaseModel, Field


class ModelThrottleResponse(BaseModel):
    """Typed response for throttled requests."""

    status_code: int = Field(default=429, description="HTTP status code")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )
    message: str = Field(default="", description="Response message")
    body: str | None = Field(default=None, description="Custom response body")

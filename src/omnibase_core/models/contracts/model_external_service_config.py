"""
External Service Configuration Model.

Defines configuration for external API calls, service
discovery, authentication, and integration patterns.
"""

from pydantic import BaseModel, Field


class ModelExternalServiceConfig(BaseModel):
    """
    External service integration patterns.

    Defines configuration for external API calls, service
    discovery, authentication, and integration patterns.
    """

    service_type: str = Field(
        ...,
        description="External service type (rest_api, graphql, grpc, message_queue, etc.)",
        min_length=1,
    )

    endpoint_url: str | None = Field(
        default=None,
        description="Service endpoint URL",
    )

    authentication_method: str = Field(
        default="none",
        description="Authentication method (none, bearer_token, api_key, oauth2)",
    )

    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting for external calls",
    )

    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Rate limit: requests per minute",
        ge=1,
    )

    connection_pooling_enabled: bool = Field(
        default=True,
        description="Enable connection pooling",
    )

    max_connections: int = Field(
        default=10,
        description="Maximum concurrent connections",
        ge=1,
    )

    timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


__all__ = ["ModelExternalServiceConfig"]

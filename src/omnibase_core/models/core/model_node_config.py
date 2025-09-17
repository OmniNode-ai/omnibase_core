"""Model for node configuration settings."""

from pydantic import BaseModel, Field


class ModelNodeConfig(BaseModel):
    """
    Represents configuration settings for a node.

    This model provides a type-safe alternative to untyped dictionaries for
    node configuration parameters.
    """

    node_name: str = Field(description="Name of the node being configured")

    enabled: bool = Field(default=True, description="Whether the node is enabled")

    timeout_seconds: int | None = Field(
        default=None,
        description="Timeout for node operations in seconds",
    )

    max_retries: int | None = Field(
        default=None,
        description="Maximum number of retries for failed operations",
    )

    custom_settings: dict[str, str] | None = Field(
        default=None,
        description="Custom string-based settings specific to the node",
    )

    environment_overrides: dict[str, str] | None = Field(
        default=None,
        description="Environment variable overrides for the node",
    )

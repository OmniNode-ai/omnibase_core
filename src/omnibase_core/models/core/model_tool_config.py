"""Model for tool configuration settings."""

from pydantic import BaseModel, Field


class ModelToolConfig(BaseModel):
    """
    Represents configuration settings for a tool.

    This model provides a type-safe alternative to untyped dict[str, Any]ionaries for
    tool configuration parameters.
    """

    tool_name: str = Field(description="Name of the tool being configured")

    enabled: bool = Field(default=True, description="Whether the tool is enabled")

    timeout_seconds: int | None = Field(
        default=None,
        description="Timeout for tool operations in seconds",
    )

    max_retries: int | None = Field(
        default=None,
        description="Maximum number of retries for failed operations",
    )

    custom_settings: dict[str, str] | None = Field(
        default=None,
        description="Custom string-based settings specific to the tool",
    )

    environment_overrides: dict[str, str] | None = Field(
        default=None,
        description="Environment variable overrides for the tool",
    )

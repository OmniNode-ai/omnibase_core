"""
Model for provider metadata to replace Dict[str, Any] patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelProviderMetadata(BaseModel):
    """Generic metadata container for provider-specific configuration."""

    # Common fields that might be in additional_config
    api_version: str | None = Field(default=None, description="API version to use")

    organization_id: str | None = Field(
        default=None,
        description="Organization ID for the provider",
    )

    project_id: str | None = Field(
        default=None,
        description="Project ID for the provider",
    )

    region: str | None = Field(
        default=None,
        description="Region or location for the provider",
    )

    custom_headers: dict[str, str] | None = Field(
        default=None,
        description="Custom HTTP headers to include",
    )

    retry_config: dict[str, int | float] | None = Field(
        default=None,
        description="Retry configuration settings",
    )

    model_config = ConfigDict(extra="allow")  # Allow additional fields

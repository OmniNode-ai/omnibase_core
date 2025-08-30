"""
Model for provider metadata to replace Dict[str, Any] patterns.
"""

from typing import Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ModelProviderMetadata(BaseModel):
    """Generic metadata container for provider-specific configuration."""

    # Common fields that might be in additional_config
    api_version: Optional[str] = Field(default=None, description="API version to use")

    organization_id: Optional[str] = Field(
        default=None, description="Organization ID for the provider"
    )

    project_id: Optional[str] = Field(
        default=None, description="Project ID for the provider"
    )

    region: Optional[str] = Field(
        default=None, description="Region or location for the provider"
    )

    custom_headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom HTTP headers to include"
    )

    retry_config: Optional[Dict[str, Union[int, float]]] = Field(
        default=None, description="Retry configuration settings"
    )

    model_config = ConfigDict(extra="allow")  # Allow additional fields

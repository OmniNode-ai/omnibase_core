from pydantic import Field, field_validator

"""
Service Endpoint Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceEndpoint for service endpoint configuration.
Extracted from model_service_configuration.py for modular architecture compliance.

Author: OmniNode Team
"""

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ModelServiceEndpoint(BaseModel):
    """Strongly typed service endpoint configuration."""

    url: HttpUrl = Field(
        ...,
        description="Service endpoint URL (http/https/redis/postgresql/etc.)",
    )
    port: int | None = Field(
        None,
        description="Service port (extracted from URL if not specified)",
        ge=1,
        le=65535,
    )
    protocol: str | None = Field(
        None,
        description="Protocol scheme (extracted from URL if not specified)",
    )

    @field_validator("port", mode="before")
    @classmethod
    def extract_port_from_url(cls, v, values):
        """Extract port from URL if not explicitly provided."""
        if v is None and "url" in values:
            url = values["url"]
            return url.port
        return v

    @field_validator("protocol", mode="before")
    @classmethod
    def extract_protocol_from_url(cls, v, values):
        """Extract protocol from URL if not explicitly provided."""
        if v is None and "url" in values:
            url = values["url"]
            return url.scheme
        return v

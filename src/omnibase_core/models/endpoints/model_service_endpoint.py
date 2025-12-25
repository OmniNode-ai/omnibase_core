"""
Service Endpoint Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceEndpoint for service endpoint configuration.
Extracted from model_service_configuration.py for modular architecture compliance.

"""

from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ModelServiceEndpoint(BaseModel):
    """Strongly typed service endpoint configuration."""

    url: HttpUrl = Field(
        default=...,
        description="Service endpoint URL (http/https/redis/postgresql/etc.)",
    )
    port: int | None = Field(
        default=None,
        description="Service port (extracted from URL if not specified)",
        ge=1,
        le=65535,
    )
    protocol: str | None = Field(
        default=None,
        description="Protocol scheme (extracted from URL if not specified)",
    )

    @model_validator(mode="before")
    @classmethod
    def extract_from_url(cls, data: Any) -> Any:
        """Extract port and protocol from URL if not explicitly provided.

        Note:
            This validator does NOT mutate the input dictionary. A defensive
            copy is made before any modifications to preserve caller's data.
        """
        if isinstance(data, dict):
            # Make a defensive copy to avoid mutating the caller's input
            data = data.copy()

            # Extract port from URL if not provided
            if data.get("port") is None and "url" in data:
                url = data["url"]
                if hasattr(url, "port") and url.port:
                    data["port"] = url.port

            # Extract protocol from URL if not provided
            if data.get("protocol") is None and "url" in data:
                url = data["url"]
                if hasattr(url, "scheme"):
                    data["protocol"] = url.scheme

        return data

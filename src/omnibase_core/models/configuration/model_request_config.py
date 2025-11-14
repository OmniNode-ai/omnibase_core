import json

from pydantic import Field

"""
Request configuration model.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.configuration.model_request_auth import ModelRequestAuth
from omnibase_core.models.configuration.model_request_retry_config import (
    ModelRequestRetryConfig,
)


class ModelRequestConfig(BaseModel):
    """
    Request configuration with typed fields.
    Replaces Dict[str, Any] for get_request_config() returns.
    """

    # HTTP method and URL
    method: str = Field(default="GET", description="HTTP method")
    url: str = Field(default=..., description="Request URL")

    # Headers and parameters
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    params: dict[str, str | list[str]] = Field(
        default_factory=dict,
        description="Query parameters",
    )

    # Body data - Required explicit None handling
    json_data: dict[str, Any] = Field(
        default_factory=dict, description="JSON body data"
    )
    form_data: dict[str, str] = Field(default_factory=dict, description="Form data")
    files: dict[str, str] = Field(
        default_factory=dict, description="File paths to upload"
    )

    # Authentication - Explicit type safety
    auth: ModelRequestAuth = Field(
        default_factory=lambda: ModelRequestAuth(),
        description="Authentication configuration",
    )

    # Timeouts
    connect_timeout: float = Field(
        default=10.0, description="Connection timeout in seconds"
    )
    read_timeout: float = Field(default=30.0, description="Read timeout in seconds")

    # SSL/TLS - Explicit type handling
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    ssl_cert: str = Field(default="", description="SSL client certificate path")
    ssl_key: str = Field(default="", description="SSL client key path")

    # Proxy - Explicit container type
    proxies: dict[str, str] = Field(
        default_factory=dict, description="Proxy configuration"
    )

    # Retry configuration - Explicit type safety
    retry_config: ModelRequestRetryConfig = Field(
        default_factory=lambda: ModelRequestRetryConfig(),
        description="Retry configuration",
    )

    # Advanced options
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects")
    max_redirects: int = Field(default=10, description="Maximum number of redirects")
    stream: bool = Field(default=False, description="Stream response content")

    model_config = ConfigDict()

    @property
    def masked_auth_summary(self) -> dict[str, Any]:
        """Get masked authentication summary for logging/debugging."""
        if not self.auth:
            return {}

        auth_data = self.auth.model_dump(exclude_none=True)
        if auth_data.get("auth_type") == "basic":
            return {
                "auth_type": "basic",
                "username": auth_data.get("username"),
                "password": "***MASKED***",
            }
        elif auth_data.get("auth_type") == "bearer":
            return {"auth_type": "bearer", "token": "***MASKED***"}
        return {"auth_type": auth_data.get("auth_type", "unknown")}

    @property
    def request_summary(self) -> dict[str, Any]:
        """Get clean request configuration summary."""
        return {
            "method": self.method,
            "url": self.url,
            "headers_count": len(self.headers),
            "params_count": len(self.params),
            "has_json_data": self.json_data is not None,
            "has_form_data": self.form_data is not None,
            "has_files": self.files is not None,
            "has_auth": self.auth is not None,
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "verify_ssl": self.verify_ssl,
            "follow_redirects": self.follow_redirects,
            "max_redirects": self.max_redirects,
            "stream": self.stream,
        }

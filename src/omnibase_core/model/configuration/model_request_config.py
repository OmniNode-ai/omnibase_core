"""
Request configuration model.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.configuration.model_request_auth import ModelRequestAuth
from omnibase_core.model.configuration.model_request_retry_config import (
    ModelRequestRetryConfig,
)

# Backward compatibility aliases
RequestAuth = ModelRequestAuth
RequestRetryConfig = ModelRequestRetryConfig


class ModelRequestConfig(BaseModel):
    """
    Request configuration with typed fields.
    Replaces Dict[str, Any] for get_request_config() returns.
    """

    # HTTP method and URL
    method: str = Field("GET", description="HTTP method")
    url: str = Field(..., description="Request URL")

    # Headers and parameters
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    params: dict[str, str | list[str]] = Field(
        default_factory=dict,
        description="Query parameters",
    )

    # Body data
    json_data: dict[str, Any] | None = Field(None, description="JSON body data")
    form_data: dict[str, str] | None = Field(None, description="Form data")
    files: dict[str, str] | None = Field(None, description="File paths to upload")

    # Authentication
    auth: ModelRequestAuth | None = Field(
        None,
        description="Authentication configuration",
    )

    # Timeouts
    connect_timeout: float = Field(10.0, description="Connection timeout in seconds")
    read_timeout: float = Field(30.0, description="Read timeout in seconds")

    # SSL/TLS
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    ssl_cert: str | None = Field(None, description="SSL client certificate path")
    ssl_key: str | None = Field(None, description="SSL client key path")

    # Proxy
    proxies: dict[str, str] | None = Field(None, description="Proxy configuration")

    # Retry configuration
    retry_config: ModelRequestRetryConfig | None = Field(
        None,
        description="Retry configuration",
    )

    # Advanced options
    follow_redirects: bool = Field(True, description="Follow HTTP redirects")
    max_redirects: int = Field(10, description="Maximum number of redirects")
    stream: bool = Field(False, description="Stream response content")

    model_config = ConfigDict()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # Use model_dump() as base and apply auth masking/flattening
        data = self.model_dump(exclude_none=True)
        # Flatten auth if present and mask sensitive data
        if "auth" in data and isinstance(data["auth"], dict):
            auth_data = data.pop("auth")
            if auth_data.get("auth_type") == "basic":
                data["auth"] = (auth_data.get("username"), "***MASKED***")
            elif auth_data.get("auth_type") == "bearer":
                data["headers"]["Authorization"] = "Bearer ***MASKED***"
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelRequestConfig":
        """Create from dictionary for easy migration."""
        return cls(**data)

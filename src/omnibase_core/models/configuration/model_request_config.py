"""Request configuration model."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.configuration.model_auth_summary import ModelAuthSummary
from omnibase_core.models.configuration.model_request_auth import ModelRequestAuth
from omnibase_core.models.configuration.model_request_retry_config import (
    ModelRequestRetryConfig,
)
from omnibase_core.models.configuration.model_request_summary import ModelRequestSummary
from omnibase_core.models.configuration.model_simple_json_data import (
    ModelSimpleJsonData,
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
    json_data: ModelSimpleJsonData = Field(
        default_factory=ModelSimpleJsonData, description="JSON body data"
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

    # Note on @property methods: Properties are compatible with frozen=True because
    # they don't mutate model state - they just compute and return derived values
    # from the model's immutable fields. Pydantic's frozen setting only prevents
    # field reassignment, not method calls or property access.
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @property
    def masked_auth_summary(self) -> ModelAuthSummary:
        """Get masked authentication summary for logging/debugging."""
        if not self.auth:
            return ModelAuthSummary()

        auth_data = self.auth.model_dump(exclude_none=True)
        if auth_data.get("auth_type") == "basic":
            return ModelAuthSummary(
                auth_type="basic",
                username=auth_data.get("username"),
                password="***MASKED***",  # secret-ok: masked placeholder value
            )
        elif auth_data.get("auth_type") == "bearer":
            return ModelAuthSummary(
                auth_type="bearer",
                token="***MASKED***",  # secret-ok: masked placeholder
            )
        return ModelAuthSummary(auth_type=auth_data.get("auth_type", "unknown"))

    @property
    def request_summary(self) -> ModelRequestSummary:
        """Get clean request configuration summary."""
        return ModelRequestSummary(
            method=self.method,
            url=self.url,
            headers_count=len(self.headers),
            params_count=len(self.params),
            has_json_data=self.json_data is not None,
            has_form_data=self.form_data is not None,
            has_files=self.files is not None,
            has_auth=self.auth is not None,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            verify_ssl=self.verify_ssl,
            follow_redirects=self.follow_redirects,
            max_redirects=self.max_redirects,
            stream=self.stream,
        )

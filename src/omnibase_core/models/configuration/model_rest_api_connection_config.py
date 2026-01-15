import os
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field, SecretStr, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.configuration.model_request_config import ModelRequestConfig
from omnibase_core.models.configuration.model_request_retry_config import (
    ModelRequestRetryConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.health.model_health_check_config import ModelHealthCheckConfig


class ModelRestApiConnectionConfig(BaseModel):
    """
    Enterprise-grade REST API connection configuration with comprehensive validation,
    business logic, and environment override capabilities.

    Features:
    - Strong typing with comprehensive validation
    - Environment variable override support
    - URL validation and manipulation
    - Authentication method management
    - Retry and timeout configuration
    - Header management and validation
    - Health check endpoint support
    - Rate limiting awareness
    """

    base_url: str = Field(
        default=...,
        description="Base URL for the REST API",
        pattern=r"^https?://[a-zA-Z0-9\-\.:]+(/.*)?$",
        max_length=500,
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="API key for authentication (secured)",
    )
    bearer_token: SecretStr | None = Field(
        default=None,
        description="Bearer token for authentication (secured)",
    )
    timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300,
    )
    max_retries: int = Field(
        default=3, description="Maximum number of retries", ge=0, le=10
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Additional HTTP headers",
    )

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v or not v.strip():
            msg = "Base URL cannot be empty"
            raise ModelOnexError(
                message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR
            )

        v = v.strip()

        # Parse URL to validate structure
        try:
            parsed = urlparse(v)
        except ValueError as e:
            msg = f"Invalid URL format: {e}"
            raise ModelOnexError(
                message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR
            )

        # Validate scheme
        if parsed.scheme not in ("http", "https"):
            msg = f"URL must use http or https scheme, got: {parsed.scheme}"
            raise ModelOnexError(
                message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR
            )

        # Validate host
        if not parsed.netloc:
            msg = "URL must include a host"
            raise ModelOnexError(
                message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR
            )

        # Recommend HTTPS for production
        if parsed.scheme == "http" and not any(
            localhost in parsed.netloc.lower()
            for localhost in ["localhost", "127.0.0.1"]
        ):
            # This is just a warning pattern, not a hard failure
            pass

        # Ensure URL ends without trailing slash for consistency
        if v.endswith("/") and len(v) > 1:
            v = v.rstrip("/")

        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate HTTP headers."""
        if v is not None:
            # Limit number of headers and their sizes
            if len(v) > 20:
                msg = "Too many headers (max 20)"
                raise ModelOnexError(
                    message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR
                )

            validated_headers = {}
            # Field type dict[str, str] ensures keys and values are strings
            for key, value in v.items():
                if len(key) > 100 or len(value) > 500:
                    msg = "Header key or value too long"
                    raise ModelOnexError(
                        message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR
                    )

                # Sanitize header names (convert to proper case)
                normalized_key = "-".join(
                    word.capitalize() for word in key.replace("_", "-").split("-")
                )
                validated_headers[normalized_key] = value

            return validated_headers
        return v

    # === URL Management ===

    def get_parsed_url(self) -> tuple[str, str, int, str]:
        """Parse base URL into components (scheme, host, port, path)."""
        parsed = urlparse(self.base_url)

        # Determine port
        if parsed.port:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        else:
            port = 80

        return parsed.scheme, parsed.hostname or "", port, parsed.path or "/"

    def build_endpoint_url(self, endpoint: str) -> str:
        """Build full URL for a specific endpoint."""
        if endpoint.startswith(("http://", "https://")):
            return endpoint  # Already a full URL

        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        return urljoin(self.base_url + "/", endpoint.lstrip("/"))

    def get_base_domain(self) -> str:
        """Get the base domain from the URL."""
        parsed = urlparse(self.base_url)
        return parsed.netloc

    def is_localhost(self) -> bool:
        """Check if this points to localhost."""
        _, host, _, _ = self.get_parsed_url()
        return host.lower() in ("localhost", "127.0.0.1")

    def uses_https(self) -> bool:
        """Check if this uses HTTPS."""
        return self.base_url.startswith("https://")

    # === Authentication Management ===

    def get_authentication_type(self) -> str:
        """Determine the authentication type being used."""
        if self.bearer_token:
            return "bearer_token"
        if self.api_key:
            return "api_key"
        return "none"

    def has_authentication(self) -> bool:
        """Check if any authentication is configured."""
        return bool(self.api_key or self.bearer_token)

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        auth_headers = {}

        if self.bearer_token:
            auth_headers["Authorization"] = (
                f"Bearer {self.bearer_token.get_secret_value()}"
            )
        elif self.api_key:
            # Common API key header patterns
            auth_headers["X-API-Key"] = self.api_key.get_secret_value()

        return auth_headers

    def get_masked_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with values masked."""
        auth_headers = {}

        if self.bearer_token:
            auth_headers["Authorization"] = "Bearer ***MASKED***"
        elif self.api_key:
            auth_headers["X-API-Key"] = "***MASKED***"

        return auth_headers

    # === Request Configuration ===

    def get_request_headers(self, include_auth: bool = True) -> dict[str, str]:
        """Get complete request headers including authentication."""
        all_headers = {}

        # Start with custom headers
        if self.headers:
            all_headers.update(self.headers)

        # Add authentication headers
        if include_auth:
            all_headers.update(self.get_auth_headers())

        # Ensure we have User-Agent
        if "User-Agent" not in all_headers:
            all_headers["User-Agent"] = "ONEX-API-Client/1.0"

        # Ensure we have Accept header
        if "Accept" not in all_headers:
            all_headers["Accept"] = "application/json"

        return all_headers

    def get_masked_request_headers(self) -> dict[str, str]:
        """Get request headers with sensitive values masked."""
        headers = self.get_request_headers(include_auth=False)
        headers.update(self.get_masked_auth_headers())
        return headers

    def get_request_config(self) -> ModelRequestConfig:
        """Get request configuration for HTTP clients."""
        return ModelRequestConfig(
            url=self.base_url,
            headers=self.get_request_headers(),
            read_timeout=float(self.timeout_seconds),
            verify_ssl=self.uses_https(),
            retry_config=ModelRequestRetryConfig(
                max_retries=self.max_retries if self.max_retries > 0 else 0,
                retry_delay=1.0,
                retry_backoff=2.0,
            ),
        )

    # === Security Assessment ===

    def is_secure_configuration(self) -> bool:
        """Assess if this is a secure configuration for production."""
        # Must use HTTPS for production
        if not self.uses_https() and not self.is_localhost():
            return False

        # Must have authentication for production
        if not self.has_authentication():
            return False

        # Check for reasonable timeout (not too high or too low)
        return not (self.timeout_seconds < 5 or self.timeout_seconds > 120)

    def get_security_recommendations(self) -> list[str]:
        """Get security recommendations for this configuration."""
        recommendations = []

        if not self.uses_https() and not self.is_localhost():
            recommendations.append("Use HTTPS for production API connections")

        if not self.has_authentication():
            recommendations.append(
                "Configure API authentication (API key or bearer token)",
            )

        if self.api_key and self.bearer_token:
            recommendations.append(
                "Configure only one authentication method (API key OR bearer token)",
            )

        if self.timeout_seconds > 60:
            recommendations.append("Long timeouts may cause service instability")

        if self.timeout_seconds < 10:
            recommendations.append("Very short timeouts may cause unnecessary failures")

        if self.max_retries > 5:
            recommendations.append("High retry counts may cause cascading failures")

        return recommendations

    def get_security_profile(self) -> dict[str, str]:
        """Get security profile assessment."""
        return {
            "protocol": "https" if self.uses_https() else "http",
            "authentication": self.get_authentication_type(),
            "host_type": "localhost" if self.is_localhost() else "remote",
            "overall_security": (
                "high" if self.is_secure_configuration() else "needs_improvement"
            ),
        }

    # === Performance Assessment ===

    def get_performance_profile(self) -> dict[str, str]:
        """Get performance characteristics of this configuration."""
        profile = {
            "timeout_category": "fast" if self.timeout_seconds <= 10 else "slow",
            "retry_aggressiveness": "high" if self.max_retries >= 5 else "moderate",
            "ssl_overhead": "present" if self.uses_https() else "none",
        }

        # Network latency assessment
        if self.is_localhost():
            profile["network_latency"] = "minimal"
        else:
            profile["network_latency"] = "variable"

        return profile

    def get_performance_recommendations(self) -> list[str]:
        """Get performance tuning recommendations."""
        recommendations = []

        if self.timeout_seconds > 60:
            recommendations.append(
                "Consider reducing timeout for better responsiveness",
            )

        if self.max_retries > 3 and self.timeout_seconds > 30:
            recommendations.append(
                "High retry count with long timeout may cause delays",
            )

        if self.uses_https():
            recommendations.append(
                "HTTPS adds latency - ensure adequate timeout values",
            )

        if not self.is_localhost() and self.timeout_seconds < 15:
            recommendations.append(
                "Remote APIs may need longer timeouts for reliability",
            )

        return recommendations

    # === Health Check Support ===

    def can_perform_health_check(self) -> bool:
        """Check if health check can be performed with this configuration."""
        return bool(self.base_url)

    def get_health_check_url(self, health_endpoint: str = "/health") -> str:
        """Get health check URL."""
        return self.build_endpoint_url(health_endpoint)

    def get_health_check_timeout(self) -> int:
        """Get recommended timeout for health check operations."""
        # Health checks should be faster than normal operations
        return min(self.timeout_seconds, 10)

    def get_health_check_config(self) -> ModelHealthCheckConfig:
        """Get configuration for health check requests."""
        return ModelHealthCheckConfig(
            check_path="/health",
            timeout_seconds=self.get_health_check_timeout(),
            check_headers=self.get_request_headers(),
            unhealthy_threshold=min(
                self.max_retries, 2
            ),  # Fewer failures needed for unhealthy
        )

    # === Environment Override Support ===

    def apply_environment_overrides(self) -> "ModelRestApiConnectionConfig":
        """Apply environment variable overrides for CI/local testing."""
        overrides: dict[str, str | int | SecretStr] = {}

        # Environment variable mappings
        env_mappings = {
            "ONEX_API_BASE_URL": "base_url",
            "ONEX_API_KEY": "api_key",
            "ONEX_API_BEARER_TOKEN": "bearer_token",
            "ONEX_API_TIMEOUT_SECONDS": "timeout_seconds",
            "ONEX_API_MAX_RETRIES": "max_retries",
        }

        for env_var, field_name in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Type conversion for numeric fields
                if field_name in ["timeout_seconds", "max_retries"]:
                    try:
                        overrides[field_name] = int(env_value)
                    except ValueError:
                        continue
                elif field_name in ["api_key", "bearer_token"]:
                    overrides[field_name] = SecretStr(env_value)
                else:
                    overrides[field_name] = env_value

        if overrides:
            current_data = self.model_dump()
            current_data.update(overrides)
            return ModelRestApiConnectionConfig(**current_data)

        return self

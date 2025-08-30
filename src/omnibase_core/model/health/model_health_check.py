"""
Health Check Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelHealthCheck for strongly typed health check configuration.
Provides scalable health check patterns instead of weak string typing.

Author: OmniNode Team
"""

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from omnibase_core.model.core import ModelGenericMetadata


class HealthCheckType(str, Enum):
    """Health check types supported by the system."""

    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    TCP_CONNECT = "tcp_connect"
    COMMAND = "command"
    KAFKA_ADMIN = "kafka_admin"
    CUSTOM = "custom"


class ModelHealthCheck(BaseModel):
    """Strongly typed health check configuration."""

    check_type: HealthCheckType = Field(
        ..., description="Type of health check to perform"
    )

    endpoint_path: Optional[str] = Field(
        None, description="Health check endpoint path (for HTTP checks)"
    )

    full_url: Optional[HttpUrl] = Field(
        None, description="Complete health check URL (alternative to endpoint_path)"
    )

    command: Optional[str] = Field(
        None, description="Command to execute for health check (for command type)"
    )

    expected_status_code: Optional[int] = Field(
        200, description="Expected HTTP status code for success", ge=100, le=599
    )

    expected_response_pattern: Optional[str] = Field(
        None, description="Regex pattern that response must match"
    )

    timeout_seconds: int = Field(
        5, description="Health check timeout in seconds", ge=1, le=300
    )

    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="HTTP headers to include in health check request",
    )

    metadata: Optional[ModelGenericMetadata] = Field(
        default_factory=dict, description="Additional health check configuration"
    )

    @field_validator("endpoint_path")
    def validate_endpoint_path_format(cls, v, info):
        """Ensure endpoint path starts with /"""
        if v is not None and not v.startswith("/"):
            return f"/{v}"
        return v

    @field_validator("command", mode="before")
    def validate_command_type_consistency(cls, v, info):
        """Ensure command is provided when check_type is COMMAND"""
        if hasattr(info, "data") and info.data:
            check_type = info.data.get("check_type")
            if check_type == HealthCheckType.COMMAND and not v:
                raise ValueError("command is required when check_type is COMMAND")
        return v

    @field_validator("full_url", mode="before")
    def validate_url_type_consistency(cls, v, info):
        """Ensure URL fields are consistent with check type"""
        if hasattr(info, "data") and info.data:
            check_type = info.data.get("check_type")
            if check_type in [HealthCheckType.HTTP_GET, HealthCheckType.HTTP_POST]:
                if not v and not info.data.get("endpoint_path"):
                    raise ValueError(
                        "Either full_url or endpoint_path required for HTTP checks"
                    )
        return v

    def get_effective_url(self, base_url: str = None) -> str:
        """Get the complete URL for the health check."""
        if self.full_url:
            return str(self.full_url)
        elif self.endpoint_path and base_url:
            return f"{base_url.rstrip('/')}{self.endpoint_path}"
        elif self.endpoint_path:
            return self.endpoint_path
        return ""

    def is_http_check(self) -> bool:
        """Check if this is an HTTP-based health check."""
        return self.check_type in [HealthCheckType.HTTP_GET, HealthCheckType.HTTP_POST]

    def get_effective_timeout(self) -> int:
        """Get the effective timeout value."""
        return self.timeout_seconds

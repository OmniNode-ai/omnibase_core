"""
ModelSecretHealthCheckResult: Health check result for secret configuration.

This model represents the result of a health check on secret configuration.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelSecretHealthCheckResult(BaseModel):
    """Health check result for secret configuration."""

    healthy: bool = Field(True, description="Overall health status")

    backend_available: bool = Field(
        False, description="Whether the backend is available and accessible"
    )

    config_valid: bool = Field(False, description="Whether the configuration is valid")

    issues: List[str] = Field(
        default_factory=list, description="List of health check issues"
    )

    response_time_ms: int = Field(
        0, description="Health check response time in milliseconds", ge=0
    )

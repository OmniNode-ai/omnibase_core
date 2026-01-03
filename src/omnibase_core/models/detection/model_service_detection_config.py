"""
Service Detection Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceDetectionConfig for service detection and health checking.
Extracted from model_service_configuration.py for modular architecture compliance.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from omnibase_core.models.endpoints.model_service_endpoint import ModelServiceEndpoint

if TYPE_CHECKING:
    from omnibase_core.models.health.model_health_check import ModelHealthCheck


class ModelServiceDetectionConfig(BaseModel):
    """Configuration for service detection and health checking."""

    endpoints: list[ModelServiceEndpoint] = Field(
        default=...,
        description="List of service endpoints for detection",
    )
    health_check: ModelHealthCheck | None = Field(
        default=None,
        description="Strongly typed health check configuration",
    )
    timeout: int = Field(
        default=5, description="Connection timeout in seconds", ge=1, le=300
    )
    admin_timeout: int | None = Field(
        default=None,
        description="Admin operation timeout in seconds",
        ge=1,
        le=300,
    )

    def get_effective_timeout(self) -> int:
        """Get the effective timeout, considering health check timeout if available."""
        if self.health_check:
            return min(self.timeout, self.health_check.get_effective_timeout())
        return self.timeout

    def has_health_check(self) -> bool:
        """Check if health checking is configured."""
        return self.health_check is not None

    def has_admin_timeout(self) -> bool:
        """Check if admin timeout is configured."""
        return self.admin_timeout is not None

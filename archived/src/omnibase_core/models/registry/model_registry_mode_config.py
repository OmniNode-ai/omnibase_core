"""
Registry Mode Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelRegistryModeConfig for configuring registry mode behavior.
Extracted from model_service_configuration.py for modular architecture compliance.

Author: OmniNode Team
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_fallback_strategy import (
    FallbackStrategyType,
    ModelFallbackStrategy,
)


class ModelRegistryModeConfig(BaseModel):
    """Configuration for a registry mode (production, development, etc.)."""

    required_services: list[str] = Field(
        default_factory=list,
        description="List of service names required for this mode",
    )
    fallback_strategy: ModelFallbackStrategy = Field(
        default_factory=lambda: ModelFallbackStrategy(
            strategy_type=FallbackStrategyType.BOOTSTRAP,
        ),
        description="Fallback strategy configuration when required services unavailable",
    )
    health_check_interval: int = Field(
        30,
        description="Health check interval in seconds",
        ge=5,
        le=300,
    )
    circuit_breaker_threshold: int = Field(
        5,
        description="Number of failures before circuit breaker opens",
        ge=1,
        le=20,
    )
    circuit_breaker_timeout: int = Field(
        60,
        description="Circuit breaker timeout in seconds",
        ge=10,
        le=600,
    )

    def has_required_services(self) -> bool:
        """Check if this mode has required services configured."""
        return len(self.required_services) > 0

    def is_service_required(self, service_name: str) -> bool:
        """Check if a specific service is required for this mode."""
        return service_name in self.required_services

    def get_effective_health_check_interval(self) -> int:
        """Get the effective health check interval."""
        return self.health_check_interval

    def is_circuit_breaker_enabled(self) -> bool:
        """Check if circuit breaker is effectively enabled."""
        return self.circuit_breaker_threshold > 0 and self.circuit_breaker_timeout > 0

    def add_required_service(self, service_name: str) -> None:
        """Add a service to the required services list."""
        if service_name not in self.required_services:
            self.required_services.append(service_name)

    def remove_required_service(self, service_name: str) -> None:
        """Remove a service from the required services list."""
        if service_name in self.required_services:
            self.required_services.remove(service_name)

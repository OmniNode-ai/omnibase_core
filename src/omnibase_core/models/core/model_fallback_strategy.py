"""
Fallback Strategy Model for ONEX Configuration-Driven Registry System.

This module provides the ModelFallbackStrategy for defining fallback strategies
when services are unavailable. Extracted from model_service_configuration.py
for modular architecture compliance.

Author: OmniNode Team
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_fallback_strategy_type import EnumFallbackStrategyType
from omnibase_core.models.core.model_fallback_metadata import ModelFallbackMetadata


class ModelFallbackStrategy(BaseModel):
    """Scalable fallback strategy configuration model."""

    strategy_type: EnumFallbackStrategyType = Field(
        default=..., description="The type of fallback strategy to use"
    )

    timeout_seconds: int | None = Field(
        default=30,
        description="Timeout for fallback operations in seconds",
        ge=1,
        le=300,
    )

    retry_attempts: int | None = Field(
        default=3, description="Number of retry attempts before giving up", ge=0, le=10
    )

    fallback_endpoint: str | None = Field(
        default=None, description="Alternative endpoint to use during fallback"
    )

    degraded_features: dict[str, bool] | None = Field(
        default_factory=dict, description="Feature flags for degraded mode operation"
    )

    metadata: ModelFallbackMetadata | None = Field(
        default_factory=lambda: ModelFallbackMetadata(),
        description="Strongly-typed strategy-specific configuration",
    )

    def is_degraded_mode(self) -> bool:
        """Check if this strategy operates in degraded mode."""
        return self.strategy_type in [
            EnumFallbackStrategyType.DEGRADED,
            EnumFallbackStrategyType.LOCAL,
        ]

    def get_effective_timeout(self) -> int:
        """Get the effective timeout value."""
        return self.timeout_seconds or 30

    def should_retry(self) -> bool:
        """Check if retries are enabled for this strategy."""
        return (self.retry_attempts or 0) > 0

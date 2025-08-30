"""
Fallback Strategy Model for ONEX Configuration-Driven Registry System.

This module provides the ModelFallbackStrategy for defining fallback strategies
when services are unavailable. Extracted from model_service_configuration.py
for modular architecture compliance.

Author: OmniNode Team
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class ModelFallbackMetadata(BaseModel):
    """Strongly-typed metadata model for fallback strategy configuration."""

    timeout_multiplier: Optional[float] = Field(
        None, description="Multiplier for timeout adjustments", ge=0.1, le=10.0
    )

    retry_backoff_seconds: Optional[int] = Field(
        None, description="Backoff time between retries in seconds", ge=1, le=300
    )

    feature_flags: Optional[Dict[str, bool]] = Field(
        default_factory=dict, description="Boolean feature flags for fallback behavior"
    )

    custom_properties: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="String-based custom configuration properties"
    )

    numeric_settings: Optional[Dict[str, float]] = Field(
        default_factory=dict, description="Numeric configuration values"
    )


class FallbackStrategyType(str, Enum):
    """Core fallback strategy types."""

    BOOTSTRAP = "bootstrap"
    EMERGENCY = "emergency"
    LOCAL = "local"
    DEGRADED = "degraded"
    FAIL_FAST = "fail_fast"


class ModelFallbackStrategy(BaseModel):
    """Scalable fallback strategy configuration model."""

    strategy_type: FallbackStrategyType = Field(
        ..., description="The type of fallback strategy to use"
    )

    timeout_seconds: Optional[int] = Field(
        30, description="Timeout for fallback operations in seconds", ge=1, le=300
    )

    retry_attempts: Optional[int] = Field(
        3, description="Number of retry attempts before giving up", ge=0, le=10
    )

    fallback_endpoint: Optional[str] = Field(
        None, description="Alternative endpoint to use during fallback"
    )

    degraded_features: Optional[Dict[str, bool]] = Field(
        default_factory=dict, description="Feature flags for degraded mode operation"
    )

    metadata: Optional[ModelFallbackMetadata] = Field(
        default_factory=ModelFallbackMetadata,
        description="Strongly-typed strategy-specific configuration",
    )

    def is_degraded_mode(self) -> bool:
        """Check if this strategy operates in degraded mode."""
        return self.strategy_type in [
            FallbackStrategyType.DEGRADED,
            FallbackStrategyType.LOCAL,
        ]

    def get_effective_timeout(self) -> int:
        """Get the effective timeout value."""
        return self.timeout_seconds or 30

    def should_retry(self) -> bool:
        """Check if retries are enabled for this strategy."""
        return (self.retry_attempts or 0) > 0

"""
Fallback Strategy Model for ONEX Configuration-Driven Registry System.

This module provides the ModelFallbackStrategy for defining fallback strategies
when services are unavailable. Extracted from model_service_configuration.py
for modular architecture compliance.

"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_fallback_strategy_type import EnumFallbackStrategyType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_fallback_metadata import ModelFallbackMetadata


class ModelFallbackStrategy(BaseModel):
    """Scalable fallback strategy configuration model.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    strategy_type: EnumFallbackStrategyType = Field(
        default=...,
        description="The type of fallback strategy to use",
    )

    timeout_seconds: int = Field(
        default=30,
        description="Timeout for fallback operations in seconds",
        ge=1,
        le=300,
    )

    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts before giving up",
        ge=0,
        le=10,
    )

    fallback_endpoint: str | None = Field(
        default=None,
        description="Alternative endpoint to use during fallback",
    )

    degraded_features: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags for degraded mode operation",
    )

    metadata: ModelFallbackMetadata = Field(
        default_factory=ModelFallbackMetadata,
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
        return self.timeout_seconds

    def should_retry(self) -> bool:
        """Check if retries are enabled for this strategy."""
        return self.retry_attempts > 0

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

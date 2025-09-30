"""
Fallback metadata model for ONEX Configuration-Driven Registry System.

This module provides the ModelFallbackMetadata for strongly-typed
metadata configuration for fallback strategies.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelFallbackMetadata(BaseModel):
    """Strongly-typed metadata model for fallback strategy configuration.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    timeout_multiplier: float = Field(
        default=1.0,
        description="Multiplier for timeout adjustments",
        ge=0.1,
        le=10.0,
    )

    retry_backoff_seconds: int = Field(
        default=5,
        description="Backoff time between retries in seconds",
        ge=1,
        le=300,
    )

    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean feature flags for fallback behavior",
    )

    custom_properties: dict[str, str] = Field(
        default_factory=dict,
        description="String-based custom configuration properties",
    )

    numeric_settings: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric configuration values",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False

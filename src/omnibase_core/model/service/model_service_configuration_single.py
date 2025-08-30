"""
Service Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceConfiguration for individual service configuration.
Extracted from the multi-model file for modular architecture compliance.

Author: OmniNode Team
"""

from pydantic import BaseModel, Field

from omnibase_core.model.detection.model_service_detection_config import \
    ModelServiceDetectionConfig
from omnibase_core.model.service.model_service_type import ModelServiceType


class ModelServiceConfiguration(BaseModel):
    """Configuration for a single service."""

    type: ModelServiceType = Field(
        ..., description="Strongly typed service configuration"
    )
    detection: ModelServiceDetectionConfig = Field(
        ..., description="Service detection and health check configuration"
    )
    priority: int = Field(
        1,
        description="Service priority (1=highest, higher numbers=lower priority)",
        ge=1,
    )
    required: bool = Field(
        True, description="Whether this service is required for the registry mode"
    )
    fallback_enabled: bool = Field(
        True, description="Whether to enable fallback if this service is unavailable"
    )

    def is_high_priority(self) -> bool:
        """Check if this service has high priority (priority <= 3)."""
        return self.priority <= 3

    def is_critical_service(self) -> bool:
        """Check if this service is critical (required and high priority)."""
        return self.required and self.is_high_priority()

    def supports_fallback(self) -> bool:
        """Check if fallback is enabled for this service."""
        return self.fallback_enabled

    def get_effective_priority(self) -> int:
        """Get the effective priority (required services get priority boost)."""
        if self.required:
            return max(1, self.priority - 1)  # Boost priority for required services
        return self.priority

    def get_service_type_name(self) -> str:
        """Get the service type name."""
        return self.type.get_effective_type_name()

    def has_health_checks(self) -> bool:
        """Check if health checks are configured."""
        return self.detection.has_health_check()

    def is_kafka_based(self) -> bool:
        """Check if this is a Kafka-based service."""
        return self.detection.is_kafka_service()

"""
Service Detection Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceDetectionConfig for service detection and health checking.
Extracted from model_service_configuration.py for modular architecture compliance.

Author: OmniNode Team
"""

from pydantic import BaseModel, Field

from omnibase_core.model.endpoints.model_service_endpoint import ModelServiceEndpoint
from omnibase_core.model.health.model_health_check import ModelHealthCheck
from omnibase_core.model.service.model_kafka_broker import ModelKafkaBroker


class ModelServiceDetectionConfig(BaseModel):
    """Configuration for service detection and health checking."""

    endpoints: list[ModelServiceEndpoint] = Field(
        ...,
        description="List of service endpoints for detection",
    )
    health_check: ModelHealthCheck | None = Field(
        None,
        description="Strongly typed health check configuration",
    )
    timeout: int = Field(5, description="Connection timeout in seconds", ge=1, le=300)
    admin_timeout: int | None = Field(
        None,
        description="Admin operation timeout in seconds (for Kafka, etc.)",
        ge=1,
        le=300,
    )
    brokers: list[ModelKafkaBroker] | None = Field(
        None,
        description="Kafka broker configurations (for event_bus services)",
    )

    def get_effective_timeout(self) -> int:
        """Get the effective timeout, considering health check timeout if available."""
        if self.health_check:
            return min(self.timeout, self.health_check.get_effective_timeout())
        return self.timeout

    def has_health_check(self) -> bool:
        """Check if health checking is configured."""
        return self.health_check is not None

    def is_kafka_service(self) -> bool:
        """Check if this is a Kafka-based service."""
        return self.brokers is not None and len(self.brokers) > 0

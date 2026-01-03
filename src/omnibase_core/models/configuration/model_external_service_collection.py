"""
External Service Collection Model for ONEX Configuration System.

Strongly typed model for external service configurations.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_external_service_config import (
    ModelExternalServiceConfig,
)


class ModelExternalServiceCollection(BaseModel):
    """
    Strongly typed model for external service configurations.

    Represents a collection of external services with proper type safety.
    """

    services: dict[str, ModelExternalServiceConfig] = Field(
        default_factory=dict,
        description="External service configurations by service name",
    )

    def get_service(self, service_name: str) -> ModelExternalServiceConfig | None:
        """Get an external service configuration by name."""
        return self.services.get(service_name)

    def has_service(self, service_name: str) -> bool:
        """Check if service exists in collection."""
        return service_name in self.services

    def add_service(
        self,
        service_name: str,
        config: ModelExternalServiceConfig,
    ) -> None:
        """Add or update a service configuration."""
        self.services[service_name] = config

    def remove_service(self, service_name: str) -> bool:
        """Remove a service configuration."""
        if service_name in self.services:
            del self.services[service_name]
            return True
        return False

    def get_service_count(self) -> int:
        """Get total count of services."""
        return len(self.services)

    def get_service_names(self) -> list[str]:
        """Get list of all service names."""
        return list(self.services.keys())

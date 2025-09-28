"""
Custom connection properties model for connection configuration.

Restructured using composition to reduce string field violations.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable
from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties

from .model_cloud_service_properties import ModelCloudServiceProperties
from .model_database_properties import ModelDatabaseProperties
from .model_message_queue_properties import ModelMessageQueueProperties
from .model_performance_properties import ModelPerformanceProperties


class ModelCustomConnectionProperties(BaseModel):
    """Custom properties for connection configuration.

    Restructured using composition to organize properties by concern.
    Reduces string field count through logical grouping.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # Grouped properties by concern
    database: ModelDatabaseProperties = Field(
        default_factory=lambda: ModelDatabaseProperties(),
        description="Database-specific properties",
    )

    message_queue: ModelMessageQueueProperties = Field(
        default_factory=lambda: ModelMessageQueueProperties(),
        description="Message queue/broker properties",
    )

    cloud_service: ModelCloudServiceProperties = Field(
        default_factory=lambda: ModelCloudServiceProperties(),
        description="Cloud/service-specific properties",
    )

    performance: ModelPerformanceProperties = Field(
        default_factory=lambda: ModelPerformanceProperties(),
        description="Performance tuning properties",
    )

    # Generic custom properties for extensibility
    custom_properties: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Additional custom properties with type safety",
    )

    # Factory methods
    @classmethod
    def create_database_connection(
        cls,
        database_name: str | None = None,
        schema_name: str | None = None,
        charset: str | None = None,
        collation: str | None = None,
        **kwargs: Any,
    ) -> ModelCustomConnectionProperties:
        """Create database connection properties."""
        database_props = ModelDatabaseProperties(
            database_display_name=database_name,
            schema_display_name=schema_name,
            charset=charset,
            collation=collation,
        )
        return cls(database=database_props, **kwargs)

    @classmethod
    def create_queue_connection(
        cls,
        queue_name: str | None = None,
        exchange_name: str | None = None,
        routing_key: str | None = None,
        durable: bool | None = None,
        **kwargs: Any,
    ) -> ModelCustomConnectionProperties:
        """Create message queue connection properties."""
        queue_props = ModelMessageQueueProperties(
            queue_display_name=queue_name,
            exchange_display_name=exchange_name,
            routing_key=routing_key,
            durable=durable,
        )
        return cls(message_queue=queue_props, **kwargs)

    @classmethod
    def create_service_connection(
        cls,
        service_name: str | None = None,
        instance_type: EnumInstanceType | None = None,
        region: str | None = None,
        availability_zone: str | None = None,
        **kwargs: Any,
    ) -> ModelCustomConnectionProperties:
        """Create service connection properties."""

        cloud_props = ModelCloudServiceProperties(
            service_display_name=service_name,
            instance_type=instance_type,
            region=region,
            availability_zone=availability_zone,
        )
        return cls(cloud_service=cloud_props, **kwargs)

    # Property accessors
    @property
    def database_display_name(self) -> str | None:
        """Access database display name."""
        return self.database.database_display_name

    @database_display_name.setter
    def database_display_name(self, value: str | None) -> None:
        """Set database display name."""
        self.database.database_display_name = value

    @property
    def schema_display_name(self) -> str | None:
        """Access schema display name."""
        return self.database.schema_display_name

    @schema_display_name.setter
    def schema_display_name(self, value: str | None) -> None:
        """Set schema display name."""
        self.database.schema_display_name = value

    @property
    def queue_display_name(self) -> str | None:
        """Access queue display name."""
        return self.message_queue.queue_display_name

    @queue_display_name.setter
    def queue_display_name(self, value: str | None) -> None:
        """Set queue display name."""
        self.message_queue.queue_display_name = value

    @property
    def service_display_name(self) -> str | None:
        """Access service display name."""
        return self.cloud_service.service_display_name

    @service_display_name.setter
    def service_display_name(self, value: str | None) -> None:
        """Set service display name."""
        self.cloud_service.service_display_name = value

    # Delegation methods
    def get_database_identifier(self) -> str | None:
        """Get database identifier for display purposes."""
        return self.database.get_database_identifier()

    def get_schema_identifier(self) -> str | None:
        """Get schema identifier for display purposes."""
        return self.database.get_schema_identifier()

    def get_queue_identifier(self) -> str | None:
        """Get queue identifier for display purposes."""
        return self.message_queue.get_queue_identifier()

    def get_exchange_identifier(self) -> str | None:
        """Get exchange identifier for display purposes."""
        return self.message_queue.get_exchange_identifier()

    def get_service_identifier(self) -> str | None:
        """Get service identifier for display purposes."""
        return self.cloud_service.get_service_identifier()

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

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelCustomConnectionProperties"]

"""
Custom connection properties model for connection configuration.

Restructured using composition to reduce string field violations.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field
from ..core.model_custom_properties import ModelCustomProperties
from .model_database_properties import ModelDatabaseProperties
from .model_message_queue_properties import ModelMessageQueueProperties
from .model_cloud_service_properties import ModelCloudServiceProperties
from .model_performance_properties import ModelPerformanceProperties
from ...enums.enum_instance_type import EnumInstanceType


class ModelCustomConnectionProperties(BaseModel):
    """Custom properties for connection configuration.

    Restructured using composition to organize properties by concern.
    Reduces string field count through logical grouping.
    """

    # Grouped properties by concern
    database: ModelDatabaseProperties = Field(
        default_factory=ModelDatabaseProperties,
        description="Database-specific properties"
    )

    message_queue: ModelMessageQueueProperties = Field(
        default_factory=ModelMessageQueueProperties,
        description="Message queue/broker properties"
    )

    cloud_service: ModelCloudServiceProperties = Field(
        default_factory=ModelCloudServiceProperties,
        description="Cloud/service-specific properties"
    )

    performance: ModelPerformanceProperties = Field(
        default_factory=ModelPerformanceProperties,
        description="Performance tuning properties"
    )

    # Generic custom properties for extensibility
    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Additional custom properties with type safety",
    )

    # Backward compatibility factory methods
    @classmethod
    def create_database_connection(
        cls,
        database_name: str | None = None,
        schema_name: str | None = None,
        charset: str | None = None,
        collation: str | None = None,
        **kwargs
    ) -> ModelCustomConnectionProperties:
        """Create database connection properties with backward compatibility."""
        database_props = ModelDatabaseProperties(
            database_display_name=database_name,
            schema_display_name=schema_name,
            charset=charset,
            collation=collation
        )
        return cls(database=database_props, **kwargs)

    @classmethod
    def create_queue_connection(
        cls,
        queue_name: str | None = None,
        exchange_name: str | None = None,
        routing_key: str | None = None,
        durable: bool | None = None,
        **kwargs
    ) -> ModelCustomConnectionProperties:
        """Create message queue connection properties with backward compatibility."""
        queue_props = ModelMessageQueueProperties(
            queue_display_name=queue_name,
            exchange_display_name=exchange_name,
            routing_key=routing_key,
            durable=durable
        )
        return cls(message_queue=queue_props, **kwargs)

    @classmethod
    def create_service_connection(
        cls,
        service_name: str | None = None,
        instance_type: str | EnumInstanceType | None = None,
        region: str | None = None,
        availability_zone: str | None = None,
        **kwargs
    ) -> ModelCustomConnectionProperties:
        """Create service connection properties with backward compatibility."""
        # Handle string instance types for backward compatibility
        enum_instance_type = None
        if instance_type is not None:
            if isinstance(instance_type, str):
                try:
                    enum_instance_type = EnumInstanceType(instance_type)
                except ValueError:
                    # If the string doesn't match any enum value, use a generic mapping
                    size_mapping = {
                        "small": EnumInstanceType.SMALL,
                        "medium": EnumInstanceType.MEDIUM,
                        "large": EnumInstanceType.LARGE,
                        "xlarge": EnumInstanceType.XLARGE,
                        "xxlarge": EnumInstanceType.XXLARGE,
                    }
                    enum_instance_type = size_mapping.get(instance_type.lower(), EnumInstanceType.MEDIUM)
            else:
                enum_instance_type = instance_type

        cloud_props = ModelCloudServiceProperties(
            service_display_name=service_name,
            instance_type=enum_instance_type,
            region=region,
            availability_zone=availability_zone
        )
        return cls(cloud_service=cloud_props, **kwargs)

    # Backward compatibility property accessors
    @property
    def database_display_name(self) -> str | None:
        """Backward compatibility for database_display_name."""
        return self.database.database_display_name

    @database_display_name.setter
    def database_display_name(self, value: str | None) -> None:
        """Backward compatibility setter for database_display_name."""
        self.database.database_display_name = value

    @property
    def schema_display_name(self) -> str | None:
        """Backward compatibility for schema_display_name."""
        return self.database.schema_display_name

    @schema_display_name.setter
    def schema_display_name(self, value: str | None) -> None:
        """Backward compatibility setter for schema_display_name."""
        self.database.schema_display_name = value

    @property
    def queue_display_name(self) -> str | None:
        """Backward compatibility for queue_display_name."""
        return self.message_queue.queue_display_name

    @queue_display_name.setter
    def queue_display_name(self, value: str | None) -> None:
        """Backward compatibility setter for queue_display_name."""
        self.message_queue.queue_display_name = value

    @property
    def service_display_name(self) -> str | None:
        """Backward compatibility for service_display_name."""
        return self.cloud_service.service_display_name

    @service_display_name.setter
    def service_display_name(self, value: str | None) -> None:
        """Backward compatibility setter for service_display_name."""
        self.cloud_service.service_display_name = value

    # Delegation methods for backward compatibility
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


# Export for use
__all__ = ["ModelCustomConnectionProperties"]
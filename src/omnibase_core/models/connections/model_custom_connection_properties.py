"""
Custom connection properties model for connection configuration.

Restructured using composition to reduce string field violations.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

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
        **kwargs: object,
    ) -> ModelCustomConnectionProperties:
        """Create database connection properties."""
        database_props = ModelDatabaseProperties(
            database_display_name=database_name,
            schema_display_name=schema_name,
            charset=charset,
            collation=collation,
        )

        # Extract known parameters from kwargs and validate types
        kwargs_dict = dict(kwargs)  # Convert to mutable dict for type safety
        message_queue = kwargs_dict.pop("message_queue", None)
        if message_queue is not None and not isinstance(
            message_queue, ModelMessageQueueProperties
        ):
            message_queue = ModelMessageQueueProperties()

        cloud_service = kwargs_dict.pop("cloud_service", None)
        if cloud_service is not None and not isinstance(
            cloud_service, ModelCloudServiceProperties
        ):
            cloud_service = ModelCloudServiceProperties()

        performance = kwargs_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance, ModelPerformanceProperties
        ):
            performance = ModelPerformanceProperties()

        custom_properties = kwargs_dict.pop("custom_properties", None)
        if custom_properties is not None and not isinstance(
            custom_properties, ModelCustomProperties
        ):
            custom_properties = ModelCustomProperties()

        # Call constructor with explicit parameters
        return cls(
            database=database_props,
            message_queue=message_queue or ModelMessageQueueProperties(),
            cloud_service=cloud_service or ModelCloudServiceProperties(),
            performance=performance or ModelPerformanceProperties(),
            custom_properties=custom_properties or ModelCustomProperties(),
        )

    @classmethod
    def create_queue_connection(
        cls,
        queue_name: str | None = None,
        exchange_name: str | None = None,
        routing_key: str | None = None,
        durable: bool | None = None,
        **kwargs: object,
    ) -> ModelCustomConnectionProperties:
        """Create message queue connection properties."""
        queue_props = ModelMessageQueueProperties(
            queue_display_name=queue_name,
            exchange_display_name=exchange_name,
            routing_key=routing_key,
            durable=durable,
        )

        # Extract known parameters from kwargs and validate types
        kwargs_dict = dict(kwargs)  # Convert to mutable dict for type safety
        database = kwargs_dict.pop("database", None)
        if database is not None and not isinstance(database, ModelDatabaseProperties):
            database = ModelDatabaseProperties()

        cloud_service = kwargs_dict.pop("cloud_service", None)
        if cloud_service is not None and not isinstance(
            cloud_service, ModelCloudServiceProperties
        ):
            cloud_service = ModelCloudServiceProperties()

        performance = kwargs_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance, ModelPerformanceProperties
        ):
            performance = ModelPerformanceProperties()

        custom_properties = kwargs_dict.pop("custom_properties", None)
        if custom_properties is not None and not isinstance(
            custom_properties, ModelCustomProperties
        ):
            custom_properties = ModelCustomProperties()

        # Call constructor with explicit parameters
        return cls(
            database=database or ModelDatabaseProperties(),
            message_queue=queue_props,
            cloud_service=cloud_service or ModelCloudServiceProperties(),
            performance=performance or ModelPerformanceProperties(),
            custom_properties=custom_properties or ModelCustomProperties(),
        )

    @classmethod
    def create_service_connection(
        cls,
        service_name: str | None = None,
        instance_type: EnumInstanceType | None = None,
        region: str | None = None,
        availability_zone: str | None = None,
        **kwargs: object,
    ) -> ModelCustomConnectionProperties:
        """Create service connection properties."""

        cloud_props = ModelCloudServiceProperties(
            service_display_name=service_name,
            instance_type=instance_type,
            region=region,
            availability_zone=availability_zone,
        )

        # Extract known parameters from kwargs and validate types
        kwargs_dict = dict(kwargs)  # Convert to mutable dict for type safety
        database = kwargs_dict.pop("database", None)
        if database is not None and not isinstance(database, ModelDatabaseProperties):
            database = ModelDatabaseProperties()

        message_queue = kwargs_dict.pop("message_queue", None)
        if message_queue is not None and not isinstance(
            message_queue, ModelMessageQueueProperties
        ):
            message_queue = ModelMessageQueueProperties()

        performance = kwargs_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance, ModelPerformanceProperties
        ):
            performance = ModelPerformanceProperties()

        custom_properties = kwargs_dict.pop("custom_properties", None)
        if custom_properties is not None and not isinstance(
            custom_properties, ModelCustomProperties
        ):
            custom_properties = ModelCustomProperties()

        # Call constructor with explicit parameters
        return cls(
            database=database or ModelDatabaseProperties(),
            message_queue=message_queue or ModelMessageQueueProperties(),
            cloud_service=cloud_props,
            performance=performance or ModelPerformanceProperties(),
            custom_properties=custom_properties or ModelCustomProperties(),
        )

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


# Export for use
__all__ = ["ModelCustomConnectionProperties"]

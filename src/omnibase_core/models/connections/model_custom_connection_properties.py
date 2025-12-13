"""
Custom connection properties model for connection configuration.

Restructured using composition to reduce string field violations.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict

from .model_cloud_service_properties import ModelCloudServiceProperties
from .model_database_properties import ModelDatabaseProperties
from .model_message_queue_properties import ModelMessageQueueProperties
from .model_performance_properties import ModelPerformanceProperties


class ModelCustomConnectionProperties(BaseModel):
    """Custom properties for connection configuration.

    Restructured using composition to organize properties by concern.
    Reduces string field count through logical grouping.
    Implements Core protocols:
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

    @model_validator(mode="before")
    @classmethod
    def handle_flat_init_kwargs(cls, data: Any) -> Any:
        """Handle flat kwargs during initialization by routing to nested models."""
        if not isinstance(data, dict):
            # Return non-dict data as-is for Pydantic to handle
            result: Any = data
            return result

        # Database properties
        database_kwargs = {}
        for key in [
            "database_id",
            "database_display_name",
            "schema_id",
            "schema_display_name",
            "charset",
            "collation",
        ]:
            if key in data:
                database_kwargs[key] = data.pop(key)
        if database_kwargs and "database" not in data:
            data["database"] = database_kwargs

        # Message queue properties
        queue_kwargs = {}
        for key in [
            "queue_id",
            "queue_display_name",
            "exchange_id",
            "exchange_display_name",
            "routing_key",
            "durable",
        ]:
            if key in data:
                queue_kwargs[key] = data.pop(key)
        if queue_kwargs and "message_queue" not in data:
            data["message_queue"] = queue_kwargs

        # Cloud service properties
        cloud_kwargs = {}
        for key in [
            "service_id",
            "service_display_name",
            "region",
            "availability_zone",
            "instance_type",
        ]:
            if key in data:
                cloud_kwargs[key] = data.pop(key)
        if cloud_kwargs and "cloud_service" not in data:
            data["cloud_service"] = cloud_kwargs

        # Performance properties
        perf_kwargs = {}
        for key in [
            "max_connections",
            "connection_limit",
            "command_timeout",
            "enable_compression",
            "compression_level",
            "enable_caching",
        ]:
            if key in data:
                perf_kwargs[key] = data.pop(key)
        if perf_kwargs and "performance" not in data:
            data["performance"] = perf_kwargs

        # Type narrowing: data is confirmed to be a dict at this point
        typed_result: dict[str, object] = data
        return typed_result

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
        kwargs_dict = dict(kwargs)  # Convert to mutable dict[str, Any]for type safety
        message_queue = kwargs_dict.pop("message_queue", None)
        if message_queue is not None and not isinstance(
            message_queue,
            ModelMessageQueueProperties,
        ):
            message_queue = ModelMessageQueueProperties()

        cloud_service = kwargs_dict.pop("cloud_service", None)
        if cloud_service is not None and not isinstance(
            cloud_service,
            ModelCloudServiceProperties,
        ):
            cloud_service = ModelCloudServiceProperties()

        performance = kwargs_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance,
            ModelPerformanceProperties,
        ):
            performance = ModelPerformanceProperties()

        custom_properties = kwargs_dict.pop("custom_properties", None)
        if custom_properties is not None and not isinstance(
            custom_properties,
            ModelCustomProperties,
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
        kwargs_dict = dict(kwargs)  # Convert to mutable dict[str, Any]for type safety
        database = kwargs_dict.pop("database", None)
        if database is not None and not isinstance(database, ModelDatabaseProperties):
            database = ModelDatabaseProperties()

        cloud_service = kwargs_dict.pop("cloud_service", None)
        if cloud_service is not None and not isinstance(
            cloud_service,
            ModelCloudServiceProperties,
        ):
            cloud_service = ModelCloudServiceProperties()

        performance = kwargs_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance,
            ModelPerformanceProperties,
        ):
            performance = ModelPerformanceProperties()

        custom_properties = kwargs_dict.pop("custom_properties", None)
        if custom_properties is not None and not isinstance(
            custom_properties,
            ModelCustomProperties,
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
        instance_type: object = None,
        region: str | None = None,
        availability_zone: str | None = None,
        **kwargs: object,
    ) -> ModelCustomConnectionProperties:
        """Create service connection properties."""

        # Handle instance_type conversion with fallback for unknown strings
        final_instance_type: EnumInstanceType | None = None

        if instance_type is None:
            # Keep final_instance_type as None
            pass
        elif isinstance(instance_type, EnumInstanceType):
            final_instance_type = instance_type
        elif isinstance(instance_type, str):
            try:
                # Try to convert string to enum
                final_instance_type = EnumInstanceType(instance_type)
            except ValueError:
                # If conversion fails, try to find a match by name
                for enum_val in EnumInstanceType:
                    if (
                        enum_val.name.lower() == instance_type.lower()
                        or enum_val.value == instance_type
                    ):
                        final_instance_type = enum_val
                        break
                else:
                    # No match found, use default fallback
                    final_instance_type = EnumInstanceType.MEDIUM

        cloud_props = ModelCloudServiceProperties(
            service_display_name=service_name,
            instance_type=final_instance_type,
            region=region,
            availability_zone=availability_zone,
        )

        # Extract known parameters from kwargs and validate types
        kwargs_dict = dict(kwargs)  # Convert to mutable dict[str, Any]for type safety
        database = kwargs_dict.pop("database", None)
        if database is not None and not isinstance(database, ModelDatabaseProperties):
            database = ModelDatabaseProperties()

        message_queue = kwargs_dict.pop("message_queue", None)
        if message_queue is not None and not isinstance(
            message_queue,
            ModelMessageQueueProperties,
        ):
            message_queue = ModelMessageQueueProperties()

        performance = kwargs_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance,
            ModelPerformanceProperties,
        ):
            performance = ModelPerformanceProperties()

        custom_properties = kwargs_dict.pop("custom_properties", None)
        if custom_properties is not None and not isinstance(
            custom_properties,
            ModelCustomProperties,
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
    def database_id(self) -> UUID | None:
        """Access database ID."""
        return self.database.database_id

    @database_id.setter
    def database_id(self, value: UUID | None) -> None:
        """Set database ID."""
        self.database.database_id = value

    @property
    def database_display_name(self) -> str | None:
        """Access database display name."""
        return self.database.database_display_name

    @database_display_name.setter
    def database_display_name(self, value: str | None) -> None:
        """Set database display name."""
        self.database.database_display_name = value

    @property
    def schema_id(self) -> UUID | None:
        """Access schema ID."""
        return self.database.schema_id

    @schema_id.setter
    def schema_id(self, value: UUID | None) -> None:
        """Set schema ID."""
        self.database.schema_id = value

    @property
    def schema_display_name(self) -> str | None:
        """Access schema display name."""
        return self.database.schema_display_name

    @schema_display_name.setter
    def schema_display_name(self, value: str | None) -> None:
        """Set schema display name."""
        self.database.schema_display_name = value

    @property
    def charset(self) -> str | None:
        """Access database charset."""
        return self.database.charset

    @charset.setter
    def charset(self, value: str | None) -> None:
        """Set database charset."""
        self.database.charset = value

    @property
    def collation(self) -> str | None:
        """Access database collation."""
        return self.database.collation

    @collation.setter
    def collation(self, value: str | None) -> None:
        """Set database collation."""
        self.database.collation = value

    @property
    def queue_id(self) -> UUID | None:
        """Access queue ID."""
        return self.message_queue.queue_id

    @queue_id.setter
    def queue_id(self, value: UUID | None) -> None:
        """Set queue ID."""
        self.message_queue.queue_id = value

    @property
    def queue_display_name(self) -> str | None:
        """Access queue display name."""
        return self.message_queue.queue_display_name

    @queue_display_name.setter
    def queue_display_name(self, value: str | None) -> None:
        """Set queue display name."""
        self.message_queue.queue_display_name = value

    @property
    def exchange_id(self) -> UUID | None:
        """Access exchange ID."""
        return self.message_queue.exchange_id

    @exchange_id.setter
    def exchange_id(self, value: UUID | None) -> None:
        """Set exchange ID."""
        self.message_queue.exchange_id = value

    @property
    def exchange_display_name(self) -> str | None:
        """Access exchange display name."""
        return self.message_queue.exchange_display_name

    @exchange_display_name.setter
    def exchange_display_name(self, value: str | None) -> None:
        """Set exchange display name."""
        self.message_queue.exchange_display_name = value

    @property
    def service_display_name(self) -> str | None:
        """Access service display name."""
        return self.cloud_service.service_display_name

    @service_display_name.setter
    def service_display_name(self, value: str | None) -> None:
        """Set service display name."""
        self.cloud_service.service_display_name = value

    @property
    def instance_type(self) -> EnumInstanceType | None:
        """Access instance type."""
        return self.cloud_service.instance_type

    @instance_type.setter
    def instance_type(self, value: EnumInstanceType | None) -> None:
        """Set instance type."""
        self.cloud_service.instance_type = value

    @property
    def region(self) -> str | None:
        """Access region."""
        return self.cloud_service.region

    @region.setter
    def region(self, value: str | None) -> None:
        """Set region."""
        self.cloud_service.region = value

    @property
    def service_id(self) -> UUID | None:
        """Access service ID."""
        return self.cloud_service.service_id

    @service_id.setter
    def service_id(self, value: UUID | None) -> None:
        """Set service ID."""
        self.cloud_service.service_id = value

    @property
    def availability_zone(self) -> str | None:
        """Access availability zone."""
        return self.cloud_service.availability_zone

    @availability_zone.setter
    def availability_zone(self, value: str | None) -> None:
        """Set availability zone."""
        self.cloud_service.availability_zone = value

    @property
    def routing_key(self) -> str | None:
        """Access routing key."""
        return self.message_queue.routing_key

    @routing_key.setter
    def routing_key(self, value: str | None) -> None:
        """Set routing key."""
        self.message_queue.routing_key = value

    @property
    def durable(self) -> bool | None:
        """Access durable setting."""
        return self.message_queue.durable

    @durable.setter
    def durable(self, value: bool | None) -> None:
        """Set durable setting."""
        self.message_queue.durable = value

    @property
    def max_connections(self) -> int:
        """Access max connections."""
        return self.performance.max_connections

    @max_connections.setter
    def max_connections(self, value: int) -> None:
        """Set max connections."""
        self.performance.max_connections = value

    @property
    def enable_compression(self) -> bool:
        """Access enable compression."""
        return self.performance.enable_compression

    @enable_compression.setter
    def enable_compression(self, value: bool) -> None:
        """Set enable compression."""
        self.performance.enable_compression = value

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelCustomConnectionProperties"]

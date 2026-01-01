"""
Custom connection properties model for connection configuration.

Restructured using composition to reduce string field violations.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict

from .model_cloud_service_properties import ModelCloudServiceProperties
from .model_database_properties import ModelDatabaseProperties
from .model_message_queue_properties import ModelMessageQueueProperties
from .model_performance_properties import ModelPerformanceProperties


def _coerce_to_model[ModelT: BaseModel](
    value: object, model_type: type[ModelT]
) -> ModelT:
    """Coerce a value to a Pydantic model using duck typing.

    Uses Pydantic's model_validate() which handles structural validation:
    - Dict/mapping inputs: Coerces to model instance
    - Existing model instances: Validates and returns
    - None: Returns default model instance
    - Invalid inputs: Returns default model instance (lenient mode)

    This follows duck typing principles - validation is based on
    structural compatibility rather than explicit isinstance checks.
    See ONEX guidelines: "Use duck typing with protocols instead of
    isinstance checks for type validation."

    Args:
        value: The value to coerce (dict, model instance, or None)
        model_type: The target Pydantic model class

    Returns:
        A validated instance of model_type
    """
    if value is None:
        return model_type()
    try:
        # model_validate handles both dicts and existing instances via duck typing
        return model_type.model_validate(value)
    except ValidationError:
        # Lenient mode: return default on validation failure
        # This maintains backward compatibility with the original behavior
        return model_type()


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
    def handle_flat_init_kwargs(cls, data: object) -> object:
        """Handle flat kwargs during initialization by routing to nested models."""
        if not isinstance(data, dict):
            # Return non-dict data as-is for Pydantic to handle
            result: object = data
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

        # Extract known parameters from kwargs and coerce to models using duck typing.
        # Uses Pydantic validation instead of isinstance checks per ONEX guidelines.
        kwargs_dict = dict(kwargs)  # Convert to mutable dict for type safety

        # Call constructor with coerced parameters
        return cls(
            database=database_props,
            message_queue=_coerce_to_model(
                kwargs_dict.pop("message_queue", None), ModelMessageQueueProperties
            ),
            cloud_service=_coerce_to_model(
                kwargs_dict.pop("cloud_service", None), ModelCloudServiceProperties
            ),
            performance=_coerce_to_model(
                kwargs_dict.pop("performance", None), ModelPerformanceProperties
            ),
            custom_properties=_coerce_to_model(
                kwargs_dict.pop("custom_properties", None), ModelCustomProperties
            ),
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

        # Extract known parameters from kwargs and coerce to models using duck typing.
        # Uses Pydantic validation instead of isinstance checks per ONEX guidelines.
        kwargs_dict = dict(kwargs)  # Convert to mutable dict for type safety

        # Call constructor with coerced parameters
        return cls(
            database=_coerce_to_model(
                kwargs_dict.pop("database", None), ModelDatabaseProperties
            ),
            message_queue=queue_props,
            cloud_service=_coerce_to_model(
                kwargs_dict.pop("cloud_service", None), ModelCloudServiceProperties
            ),
            performance=_coerce_to_model(
                kwargs_dict.pop("performance", None), ModelPerformanceProperties
            ),
            custom_properties=_coerce_to_model(
                kwargs_dict.pop("custom_properties", None), ModelCustomProperties
            ),
        )

    @classmethod
    def create_service_connection(
        cls,
        service_name: str | None = None,
        instance_type: EnumInstanceType | str | None = None,
        region: str | None = None,
        availability_zone: str | None = None,
        **kwargs: object,
    ) -> ModelCustomConnectionProperties:
        """Create service connection properties.

        Args:
            service_name: Display name for the service
            instance_type: Instance type as enum or string (e.g., "MEDIUM", "LARGE").
                Accepts EnumInstanceType values directly, string representations that
                will be coerced to the enum, or None for no instance type.
            region: Cloud region identifier
            availability_zone: Availability zone within the region
            **kwargs: Additional properties passed to nested models

        Returns:
            Configured ModelCustomConnectionProperties instance
        """
        # Handle instance_type conversion with fallback for unknown strings.
        # NOTE: The isinstance checks below for EnumInstanceType and str are justified
        # for type-based dispatch during enum coercion. This is different from type
        # validation - we need to know the type to apply the correct conversion logic.
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

        # Extract known parameters from kwargs and coerce to models using duck typing.
        # Uses Pydantic validation instead of isinstance checks per ONEX guidelines.
        kwargs_dict = dict(kwargs)  # Convert to mutable dict for type safety

        # Call constructor with coerced parameters
        return cls(
            database=_coerce_to_model(
                kwargs_dict.pop("database", None), ModelDatabaseProperties
            ),
            message_queue=_coerce_to_model(
                kwargs_dict.pop("message_queue", None), ModelMessageQueueProperties
            ),
            cloud_service=cloud_props,
            performance=_coerce_to_model(
                kwargs_dict.pop("performance", None), ModelPerformanceProperties
            ),
            custom_properties=_coerce_to_model(
                kwargs_dict.pop("custom_properties", None), ModelCustomProperties
            ),
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
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If configuration fails due to validation errors,
                type mismatches, or attribute access issues.
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (ValidationError, ValueError, TypeError, AttributeError) as e:
            # ValidationError: Pydantic validation failure (validate_assignment=True)
            # ValueError: Custom validator rejection or invalid value
            # TypeError: Type coercion failure
            # AttributeError: Read-only attribute or access issue
            raise ModelOnexError(
                message=f"Configuration failed for property: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"failed_keys": list(kwargs.keys())},
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        This base implementation always returns True. Subclasses should override
        this method to perform custom validation and catch specific exceptions
        (e.g., ValidationError, ValueError) when implementing validation logic.
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelCustomConnectionProperties"]

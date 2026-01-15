"""
Custom connection properties model for connection configuration.

Restructured using composition to reduce string field violations.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

import logging
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

# Module-level logger for coercion observability
_logger = logging.getLogger(__name__)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict

from .model_cloud_service_properties import ModelCloudServiceProperties
from .model_database_properties import ModelDatabaseProperties
from .model_message_queue_properties import ModelMessageQueueProperties
from .model_performance_properties import ModelPerformanceProperties


def _coerce_to_model[ModelT: BaseModel](
    value: object, model_type: type[ModelT], field_name: str = "unknown"
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
        field_name: Name of the field being coerced (for logging context)

    Returns:
        A validated instance of model_type
    """
    if value is None:
        _logger.debug(
            "Coercion: field=%s target_type=%s original_value=None "
            "-> returning default instance",
            field_name,
            model_type.__name__,
        )
        return model_type()
    try:
        # model_validate handles both dicts and existing instances via duck typing
        result = model_type.model_validate(value)
        _logger.debug(
            "Coercion: field=%s target_type=%s original_type=%s "
            "-> validated successfully",
            field_name,
            model_type.__name__,
            type(value).__name__,
        )
        return result
    except ValidationError as e:
        # Lenient mode: return default on validation failure
        # fallback-ok: graceful degradation when coercion fails
        _logger.debug(
            "Coercion: field=%s target_type=%s original_type=%s original_value=%r "
            "-> validation failed, returning default instance. Error: %s",
            field_name,
            model_type.__name__,
            type(value).__name__,
            value,
            str(e),
        )
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
        """Create database connection properties with optional nested model configuration.

        This factory method creates a connection properties instance configured for
        database connections. The primary database properties are set from the explicit
        parameters, while other nested models can be provided via kwargs.

        Args:
            database_name: Display name for the database.
            schema_name: Display name for the schema.
            charset: Database character set (e.g., "utf8", "utf8mb4").
            collation: Database collation (e.g., "utf8_general_ci").
            **kwargs: Optional nested model configuration. Supported keys:
                - message_queue: Dict or ModelMessageQueueProperties instance
                - cloud_service: Dict or ModelCloudServiceProperties instance
                - performance: Dict or ModelPerformanceProperties instance
                - custom_properties: Dict or ModelCustomProperties instance

        Returns:
            Configured ModelCustomConnectionProperties instance.

        Note:
            Kwargs handling follows duck typing principles per ONEX guidelines:
            - Dict values are coerced to the appropriate model type via Pydantic validation
            - Existing model instances are validated and passed through
            - None values result in default model instances
            - Invalid types (non-dict, non-model) return default model instances (lenient mode)
            - Unknown kwargs (not in the supported keys list) are silently ignored

        Example:
            >>> props = ModelCustomConnectionProperties.create_database_connection(
            ...     database_name="orders_db",
            ...     charset="utf8mb4",
            ...     performance={"max_connections": 200, "enable_compression": True},
            ...     cloud_service={"region": "us-west-2"},
            ... )
        """
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
                kwargs_dict.pop("message_queue", None),
                ModelMessageQueueProperties,
                "message_queue",
            ),
            cloud_service=_coerce_to_model(
                kwargs_dict.pop("cloud_service", None),
                ModelCloudServiceProperties,
                "cloud_service",
            ),
            performance=_coerce_to_model(
                kwargs_dict.pop("performance", None),
                ModelPerformanceProperties,
                "performance",
            ),
            custom_properties=_coerce_to_model(
                kwargs_dict.pop("custom_properties", None),
                ModelCustomProperties,
                "custom_properties",
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
        """Create message queue connection properties with optional nested model configuration.

        This factory method creates a connection properties instance configured for
        message queue/broker connections. The primary queue properties are set from
        the explicit parameters, while other nested models can be provided via kwargs.

        Args:
            queue_name: Display name for the queue.
            exchange_name: Display name for the exchange.
            routing_key: Routing key for message routing (e.g., "orders.created").
            durable: Whether the queue/exchange should survive broker restarts.
            **kwargs: Optional nested model configuration. Supported keys:
                - database: Dict or ModelDatabaseProperties instance
                - cloud_service: Dict or ModelCloudServiceProperties instance
                - performance: Dict or ModelPerformanceProperties instance
                - custom_properties: Dict or ModelCustomProperties instance

        Returns:
            Configured ModelCustomConnectionProperties instance.

        Note:
            Kwargs handling follows duck typing principles per ONEX guidelines:
            - Dict values are coerced to the appropriate model type via Pydantic validation
            - Existing model instances are validated and passed through
            - None values result in default model instances
            - Invalid types (non-dict, non-model) return default model instances (lenient mode)
            - Unknown kwargs (not in the supported keys list) are silently ignored

        Example:
            >>> props = ModelCustomConnectionProperties.create_queue_connection(
            ...     queue_name="events_queue",
            ...     exchange_name="events_exchange",
            ...     routing_key="events.#",
            ...     durable=True,
            ...     performance={"max_connections": 150},
            ... )
        """
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
                kwargs_dict.pop("database", None),
                ModelDatabaseProperties,
                "database",
            ),
            message_queue=queue_props,
            cloud_service=_coerce_to_model(
                kwargs_dict.pop("cloud_service", None),
                ModelCloudServiceProperties,
                "cloud_service",
            ),
            performance=_coerce_to_model(
                kwargs_dict.pop("performance", None),
                ModelPerformanceProperties,
                "performance",
            ),
            custom_properties=_coerce_to_model(
                kwargs_dict.pop("custom_properties", None),
                ModelCustomProperties,
                "custom_properties",
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
        """Create service connection properties with optional nested model configuration.

        This factory method creates a connection properties instance configured for
        cloud service connections. The primary service properties are set from the
        explicit parameters, while other nested models can be provided via kwargs.

        Args:
            service_name: Display name for the service.
            instance_type: Instance type as enum or string (e.g., "MEDIUM", "LARGE").
                Accepts EnumInstanceType values directly, string representations that
                will be coerced to the enum, or None for no instance type. Unknown
                strings fall back to EnumInstanceType.MEDIUM.
            region: Cloud region identifier (e.g., "us-west-2", "eu-central-1").
            availability_zone: Availability zone within the region (e.g., "us-west-2a").
            **kwargs: Optional nested model configuration. Supported keys:
                - database: Dict or ModelDatabaseProperties instance
                - message_queue: Dict or ModelMessageQueueProperties instance
                - performance: Dict or ModelPerformanceProperties instance
                - custom_properties: Dict or ModelCustomProperties instance

        Returns:
            Configured ModelCustomConnectionProperties instance.

        Note:
            Kwargs handling follows duck typing principles per ONEX guidelines:
            - Dict values are coerced to the appropriate model type via Pydantic validation
            - Existing model instances are validated and passed through
            - None values result in default model instances
            - Invalid types (non-dict, non-model) return default model instances (lenient mode)
            - Unknown kwargs (not in the supported keys list) are silently ignored

        Example:
            >>> props = ModelCustomConnectionProperties.create_service_connection(
            ...     service_name="api-gateway",
            ...     instance_type=EnumInstanceType.T3_LARGE,
            ...     region="us-east-1",
            ...     database={"database_display_name": "gateway_db"},
            ...     performance={"max_connections": 1000},
            ... )
        """
        # Handle instance_type conversion with fallback for unknown strings.
        # NOTE: The isinstance checks below for EnumInstanceType and str are justified
        # for type-based dispatch during enum coercion. This is different from type
        # validation - we need to know the type to apply the correct conversion logic.
        final_instance_type: EnumInstanceType | None = None

        if instance_type is None:
            # Keep final_instance_type as None
            _logger.debug(
                "Coercion: field=instance_type target_type=EnumInstanceType "
                "original_value=None -> keeping as None"
            )
        elif isinstance(instance_type, EnumInstanceType):
            final_instance_type = instance_type
            _logger.debug(
                "Coercion: field=instance_type target_type=EnumInstanceType "
                "original_type=EnumInstanceType original_value=%s -> no coercion needed",
                instance_type.value,
            )
        elif isinstance(instance_type, str):
            try:
                # Try to convert string to enum
                final_instance_type = EnumInstanceType(instance_type)
                _logger.debug(
                    "Coercion: field=instance_type target_type=EnumInstanceType "
                    "original_type=str original_value=%r -> coerced to %s",
                    instance_type,
                    final_instance_type.value,
                )
            except ValueError:
                # If conversion fails, try to find a match by name
                for enum_val in EnumInstanceType:
                    if (
                        enum_val.name.lower() == instance_type.lower()
                        or enum_val.value == instance_type
                    ):
                        final_instance_type = enum_val
                        _logger.debug(
                            "Coercion: field=instance_type target_type=EnumInstanceType "
                            "original_type=str original_value=%r -> coerced via name match to %s",
                            instance_type,
                            final_instance_type.value,
                        )
                        break
                else:
                    # No match found, use default fallback
                    final_instance_type = EnumInstanceType.MEDIUM
                    _logger.debug(
                        "Coercion: field=instance_type target_type=EnumInstanceType "
                        "original_type=str original_value=%r -> unknown value, "
                        "falling back to default MEDIUM",
                        instance_type,
                    )

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
                kwargs_dict.pop("database", None),
                ModelDatabaseProperties,
                "database",
            ),
            message_queue=_coerce_to_model(
                kwargs_dict.pop("message_queue", None),
                ModelMessageQueueProperties,
                "message_queue",
            ),
            cloud_service=cloud_props,
            performance=_coerce_to_model(
                kwargs_dict.pop("performance", None),
                ModelPerformanceProperties,
                "performance",
            ),
            custom_properties=_coerce_to_model(
                kwargs_dict.pop("custom_properties", None),
                ModelCustomProperties,
                "custom_properties",
            ),
        )

    # Property accessors
    @property
    def database_id(self) -> UUID | None:
        return self.database.database_id

    @database_id.setter
    def database_id(self, value: UUID | None) -> None:
        self.database.database_id = value

    @property
    def database_display_name(self) -> str | None:
        return self.database.database_display_name

    @database_display_name.setter
    def database_display_name(self, value: str | None) -> None:
        self.database.database_display_name = value

    @property
    def schema_id(self) -> UUID | None:
        return self.database.schema_id

    @schema_id.setter
    def schema_id(self, value: UUID | None) -> None:
        self.database.schema_id = value

    @property
    def schema_display_name(self) -> str | None:
        return self.database.schema_display_name

    @schema_display_name.setter
    def schema_display_name(self, value: str | None) -> None:
        self.database.schema_display_name = value

    @property
    def charset(self) -> str | None:
        return self.database.charset

    @charset.setter
    def charset(self, value: str | None) -> None:
        self.database.charset = value

    @property
    def collation(self) -> str | None:
        return self.database.collation

    @collation.setter
    def collation(self, value: str | None) -> None:
        self.database.collation = value

    @property
    def queue_id(self) -> UUID | None:
        return self.message_queue.queue_id

    @queue_id.setter
    def queue_id(self, value: UUID | None) -> None:
        self.message_queue.queue_id = value

    @property
    def queue_display_name(self) -> str | None:
        return self.message_queue.queue_display_name

    @queue_display_name.setter
    def queue_display_name(self, value: str | None) -> None:
        self.message_queue.queue_display_name = value

    @property
    def exchange_id(self) -> UUID | None:
        return self.message_queue.exchange_id

    @exchange_id.setter
    def exchange_id(self, value: UUID | None) -> None:
        self.message_queue.exchange_id = value

    @property
    def exchange_display_name(self) -> str | None:
        return self.message_queue.exchange_display_name

    @exchange_display_name.setter
    def exchange_display_name(self, value: str | None) -> None:
        self.message_queue.exchange_display_name = value

    @property
    def service_display_name(self) -> str | None:
        return self.cloud_service.service_display_name

    @service_display_name.setter
    def service_display_name(self, value: str | None) -> None:
        self.cloud_service.service_display_name = value

    @property
    def instance_type(self) -> EnumInstanceType | None:
        return self.cloud_service.instance_type

    @instance_type.setter
    def instance_type(self, value: EnumInstanceType | None) -> None:
        self.cloud_service.instance_type = value

    @property
    def region(self) -> str | None:
        return self.cloud_service.region

    @region.setter
    def region(self, value: str | None) -> None:
        self.cloud_service.region = value

    @property
    def service_id(self) -> UUID | None:
        return self.cloud_service.service_id

    @service_id.setter
    def service_id(self, value: UUID | None) -> None:
        self.cloud_service.service_id = value

    @property
    def availability_zone(self) -> str | None:
        return self.cloud_service.availability_zone

    @availability_zone.setter
    def availability_zone(self, value: str | None) -> None:
        self.cloud_service.availability_zone = value

    @property
    def routing_key(self) -> str | None:
        return self.message_queue.routing_key

    @routing_key.setter
    def routing_key(self, value: str | None) -> None:
        self.message_queue.routing_key = value

    @property
    def durable(self) -> bool | None:
        return self.message_queue.durable

    @durable.setter
    def durable(self, value: bool | None) -> None:
        self.message_queue.durable = value

    @property
    def max_connections(self) -> int:
        return self.performance.max_connections

    @max_connections.setter
    def max_connections(self, value: int) -> None:
        self.performance.max_connections = value

    @property
    def enable_compression(self) -> bool:
        return self.performance.enable_compression

    @enable_compression.setter
    def enable_compression(self, value: bool) -> None:
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

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
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS: ValidationError, ValueError, TypeError, AttributeError
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

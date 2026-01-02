"""
Test module for ModelCustomConnectionProperties.

Tests the refactored connection properties model with UUID references
and backward compatibility factory methods.
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.models.connections.model_custom_connection_properties import (
    ModelCustomConnectionProperties,
)


@pytest.mark.unit
class TestModelCustomConnectionProperties:
    """Test cases for ModelCustomConnectionProperties."""

    def test_default_initialization(self):
        """Test default initialization of the model."""
        props = ModelCustomConnectionProperties()

        # All entity references should be None by default
        assert props.database_id is None
        assert props.database_display_name is None
        assert props.schema_id is None
        assert props.schema_display_name is None
        assert props.queue_id is None
        assert props.queue_display_name is None
        assert props.exchange_id is None
        assert props.exchange_display_name is None
        assert props.service_id is None
        assert props.service_display_name is None
        assert props.instance_type is None

    def test_database_connection_factory(self):
        """Test creating database connection with factory method."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            schema_name="test_schema",
            charset="utf8",
            collation="utf8_general_ci",
        )

        assert props.database_display_name == "test_db"
        assert props.schema_display_name == "test_schema"
        assert props.charset == "utf8"
        assert props.collation == "utf8_general_ci"
        assert props.database_id is None  # Not set by factory

    def test_queue_connection_factory(self):
        """Test creating queue connection with factory method."""
        props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="test_queue",
            exchange_name="test_exchange",
            routing_key="test.key",
            durable=True,
        )

        assert props.queue_display_name == "test_queue"
        assert props.exchange_display_name == "test_exchange"
        assert props.routing_key == "test.key"
        assert props.durable is True
        assert props.queue_id is None  # Not set by factory

    def test_service_connection_factory_with_enum(self):
        """Test creating service connection with enum instance type."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            instance_type=EnumInstanceType.T3_MEDIUM,
            region="us-west-2",
        )

        assert props.service_display_name == "test_service"
        assert props.instance_type == EnumInstanceType.T3_MEDIUM
        assert props.region == "us-west-2"
        assert props.service_id is None  # Not set by factory

    def test_service_connection_factory_with_string(self):
        """Test creating service connection with string instance type."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            instance_type="t3.medium",
        )

        assert props.service_display_name == "test_service"
        assert props.instance_type == EnumInstanceType.T3_MEDIUM

    def test_service_connection_factory_with_generic_string(self):
        """Test creating service connection with generic string instance type."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            instance_type="large",
        )

        assert props.service_display_name == "test_service"
        assert props.instance_type == EnumInstanceType.LARGE

    def test_service_connection_factory_with_unknown_string(self):
        """Test creating service connection with unknown string instance type."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            instance_type="custom_unknown_type",
        )

        assert props.service_display_name == "test_service"
        assert props.instance_type == EnumInstanceType.MEDIUM  # Default fallback

    def test_uuid_references(self):
        """Test setting UUID references directly."""
        database_id = uuid4()
        schema_id = uuid4()
        queue_id = uuid4()
        exchange_id = uuid4()
        service_id = uuid4()

        props = ModelCustomConnectionProperties(
            database_id=database_id,
            database_display_name="Display DB",
            schema_id=schema_id,
            schema_display_name="Display Schema",
            queue_id=queue_id,
            queue_display_name="Display Queue",
            exchange_id=exchange_id,
            exchange_display_name="Display Exchange",
            service_id=service_id,
            service_display_name="Display Service",
        )

        assert props.database_id == database_id
        assert props.schema_id == schema_id
        assert props.queue_id == queue_id
        assert props.exchange_id == exchange_id
        assert props.service_id == service_id

    def test_identifier_getters_with_display_names(self):
        """Test identifier getter methods with display names."""
        props = ModelCustomConnectionProperties(
            database_display_name="test_db",
            schema_display_name="test_schema",
            queue_display_name="test_queue",
            exchange_display_name="test_exchange",
            service_display_name="test_service",
        )

        assert props.get_database_identifier() == "test_db"
        assert props.get_schema_identifier() == "test_schema"
        assert props.get_queue_identifier() == "test_queue"
        assert props.get_exchange_identifier() == "test_exchange"
        assert props.get_service_identifier() == "test_service"

    def test_identifier_getters_with_uuids_only(self):
        """Test identifier getter methods with UUIDs only."""
        database_id = uuid4()
        schema_id = uuid4()
        queue_id = uuid4()
        exchange_id = uuid4()
        service_id = uuid4()

        props = ModelCustomConnectionProperties(
            database_id=database_id,
            schema_id=schema_id,
            queue_id=queue_id,
            exchange_id=exchange_id,
            service_id=service_id,
        )

        assert props.get_database_identifier() == str(database_id)
        assert props.get_schema_identifier() == str(schema_id)
        assert props.get_queue_identifier() == str(queue_id)
        assert props.get_exchange_identifier() == str(exchange_id)
        assert props.get_service_identifier() == str(service_id)

    def test_identifier_getters_with_no_values(self):
        """Test identifier getter methods with no values set."""
        props = ModelCustomConnectionProperties()

        assert props.get_database_identifier() is None
        assert props.get_schema_identifier() is None
        assert props.get_queue_identifier() is None
        assert props.get_exchange_identifier() is None
        assert props.get_service_identifier() is None

    def test_identifier_getters_display_name_priority(self):
        """Test that display names take priority over UUIDs in getters."""
        database_id = uuid4()
        schema_id = uuid4()

        props = ModelCustomConnectionProperties(
            database_id=database_id,
            database_display_name="display_db",
            schema_id=schema_id,
            schema_display_name="display_schema",
        )

        # Display names should take priority
        assert props.get_database_identifier() == "display_db"
        assert props.get_schema_identifier() == "display_schema"

    def test_instance_type_enum_validation(self):
        """Test that instance type properly validates enum values."""
        props = ModelCustomConnectionProperties(instance_type=EnumInstanceType.T3_LARGE)

        assert props.instance_type == EnumInstanceType.T3_LARGE
        assert str(props.instance_type) == "t3.large"

    def test_serialization_compatibility(self):
        """Test that the model serializes correctly for JSON compatibility."""
        props = ModelCustomConnectionProperties(
            database_display_name="test_db",
            instance_type=EnumInstanceType.T3_MEDIUM,
            max_connections=100,
            enable_compression=True,
        )

        # Test dict conversion (Pydantic serialization)
        # The model uses nested composition, so check nested structure
        data = props.model_dump()
        assert data["database"]["database_display_name"] == "test_db"
        assert data["cloud_service"]["instance_type"] == "t3.medium"
        assert data["performance"]["max_connections"] == 100
        assert data["performance"]["enable_compression"] is True

    def test_custom_properties_integration(self):
        """Test integration with custom properties."""
        props = ModelCustomConnectionProperties(database_display_name="test_db")

        # Custom properties should be initialized
        assert props.custom_properties is not None

        # Should be able to add custom properties using the correct API
        props.custom_properties.set_custom_value("custom_key", "custom_value")
        assert props.custom_properties.get_custom_value("custom_key") == "custom_value"


@pytest.mark.unit
class TestFactoryMethodsExtraKwargs:
    """Test cases for extra kwargs handling in factory methods.

    These tests verify that the factory methods properly coerce **kwargs
    to nested model objects using duck typing and Pydantic validation.
    The _coerce_to_model helper handles:
    - Dict/mapping inputs: Coerces to model instance
    - Existing model instances: Validates and returns
    - None: Returns default model instance
    - Invalid inputs: Returns default model instance (lenient mode)
    """

    # ==========================================================================
    # create_database_connection() tests
    # ==========================================================================

    def test_create_database_connection_with_dict_kwargs(self):
        """Test that dict kwargs are properly coerced to nested models."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            message_queue={"queue_display_name": "test_queue", "durable": True},
            cloud_service={"region": "us-west-2", "availability_zone": "us-west-2a"},
            performance={"max_connections": 200, "enable_compression": True},
        )

        # Verify primary database properties
        assert props.database.database_display_name == "test_db"

        # Verify message_queue was coerced from dict
        assert props.message_queue.queue_display_name == "test_queue"
        assert props.message_queue.durable is True

        # Verify cloud_service was coerced from dict
        assert props.cloud_service.region == "us-west-2"
        assert props.cloud_service.availability_zone == "us-west-2a"

        # Verify performance was coerced from dict
        assert props.performance.max_connections == 200
        assert props.performance.enable_compression is True

    def test_create_database_connection_with_model_objects(self):
        """Test that model objects are passed through correctly."""
        from omnibase_core.models.connections.model_cloud_service_properties import (
            ModelCloudServiceProperties,
        )
        from omnibase_core.models.connections.model_message_queue_properties import (
            ModelMessageQueueProperties,
        )
        from omnibase_core.models.connections.model_performance_properties import (
            ModelPerformanceProperties,
        )
        from omnibase_core.models.core.model_custom_properties import (
            ModelCustomProperties,
        )

        perf = ModelPerformanceProperties(max_connections=50, enable_caching=False)
        queue = ModelMessageQueueProperties(
            queue_display_name="my_queue", routing_key="orders.created"
        )
        cloud = ModelCloudServiceProperties(region="eu-central-1")
        custom = ModelCustomProperties()
        custom.set_custom_string("env", "production")

        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="orders_db",
            performance=perf,
            message_queue=queue,
            cloud_service=cloud,
            custom_properties=custom,
        )

        assert props.database.database_display_name == "orders_db"
        assert props.performance.max_connections == 50
        assert props.performance.enable_caching is False
        assert props.message_queue.queue_display_name == "my_queue"
        assert props.message_queue.routing_key == "orders.created"
        assert props.cloud_service.region == "eu-central-1"
        assert props.custom_properties.get_custom_value("env") == "production"

    def test_create_database_connection_with_none_kwargs(self):
        """Test that None kwargs return default model instances."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            message_queue=None,
            cloud_service=None,
            performance=None,
            custom_properties=None,
        )

        # All should be default instances with default values
        assert props.database.database_display_name == "test_db"
        assert props.message_queue.queue_display_name is None
        assert props.message_queue.durable is None
        assert props.cloud_service.region is None
        assert props.performance.max_connections == 100  # Default value
        assert props.custom_properties.is_empty() is True

    def test_create_database_connection_with_invalid_kwargs(self):
        """Test that invalid kwargs return defaults (lenient mode)."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            message_queue="invalid_string",  # Invalid type
            cloud_service=12345,  # Invalid type
            performance=["list", "of", "items"],  # Invalid type
        )

        # Should get default instances due to lenient mode
        assert props.database.database_display_name == "test_db"
        assert props.message_queue.queue_display_name is None  # Default
        assert props.cloud_service.region is None  # Default
        assert props.performance.max_connections == 100  # Default

    def test_create_database_connection_with_partial_dict(self):
        """Test that partial dicts are properly handled with defaults."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            performance={"max_connections": 500},  # Only one field
        )

        # Specified field should be set
        assert props.performance.max_connections == 500
        # Other fields should have defaults
        assert props.performance.enable_compression is False
        assert props.performance.enable_caching is True
        assert props.performance.command_timeout == 30

    # ==========================================================================
    # create_queue_connection() tests
    # ==========================================================================

    def test_create_queue_connection_with_dict_kwargs(self):
        """Test that dict kwargs are properly coerced to nested models."""
        props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="events_queue",
            exchange_name="events_exchange",
            routing_key="events.#",
            durable=True,
            database={"database_display_name": "events_db", "charset": "utf8mb4"},
            cloud_service={"service_display_name": "RabbitMQ", "region": "ap-south-1"},
            performance={"max_connections": 150, "connection_limit": 75},
        )

        # Verify primary queue properties
        assert props.message_queue.queue_display_name == "events_queue"
        assert props.message_queue.exchange_display_name == "events_exchange"
        assert props.message_queue.routing_key == "events.#"
        assert props.message_queue.durable is True

        # Verify database was coerced from dict
        assert props.database.database_display_name == "events_db"
        assert props.database.charset == "utf8mb4"

        # Verify cloud_service was coerced from dict
        assert props.cloud_service.service_display_name == "RabbitMQ"
        assert props.cloud_service.region == "ap-south-1"

        # Verify performance was coerced from dict
        assert props.performance.max_connections == 150
        assert props.performance.connection_limit == 75

    def test_create_queue_connection_with_model_objects(self):
        """Test that model objects are passed through correctly."""
        from omnibase_core.models.connections.model_database_properties import (
            ModelDatabaseProperties,
        )
        from omnibase_core.models.connections.model_performance_properties import (
            ModelPerformanceProperties,
        )

        db = ModelDatabaseProperties(
            database_display_name="queue_db", collation="utf8_unicode_ci"
        )
        perf = ModelPerformanceProperties(compression_level=9)

        props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="audit_queue",
            database=db,
            performance=perf,
        )

        assert props.message_queue.queue_display_name == "audit_queue"
        assert props.database.database_display_name == "queue_db"
        assert props.database.collation == "utf8_unicode_ci"
        assert props.performance.compression_level == 9

    def test_create_queue_connection_with_none_kwargs(self):
        """Test that None kwargs return default model instances."""
        props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="test_queue",
            database=None,
            cloud_service=None,
            performance=None,
            custom_properties=None,
        )

        assert props.message_queue.queue_display_name == "test_queue"
        assert props.database.database_display_name is None
        assert props.cloud_service.service_display_name is None
        assert props.performance.max_connections == 100  # Default
        assert props.custom_properties.is_empty() is True

    def test_create_queue_connection_with_invalid_kwargs(self):
        """Test that invalid kwargs return defaults (lenient mode)."""
        props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="test_queue",
            database=object(),  # Invalid type
            performance={"invalid_nested": {"too_deep": True}},  # Ignored extra field
        )

        # database should get default due to lenient mode
        assert props.database.database_display_name is None

        # Performance should still work (extra fields ignored by model config)
        assert props.performance.max_connections == 100

    # ==========================================================================
    # create_service_connection() tests
    # ==========================================================================

    def test_create_service_connection_with_dict_kwargs(self):
        """Test that dict kwargs are properly coerced to nested models."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="api-gateway",
            instance_type=EnumInstanceType.T3_LARGE,
            region="us-east-1",
            availability_zone="us-east-1a",
            database={"database_display_name": "gateway_db"},
            message_queue={
                "queue_display_name": "gateway_queue",
                "routing_key": "api.*",
            },
            performance={"max_connections": 1000, "enable_compression": True},
        )

        # Verify primary service properties
        assert props.cloud_service.service_display_name == "api-gateway"
        assert props.cloud_service.instance_type == EnumInstanceType.T3_LARGE
        assert props.cloud_service.region == "us-east-1"
        assert props.cloud_service.availability_zone == "us-east-1a"

        # Verify database was coerced from dict
        assert props.database.database_display_name == "gateway_db"

        # Verify message_queue was coerced from dict
        assert props.message_queue.queue_display_name == "gateway_queue"
        assert props.message_queue.routing_key == "api.*"

        # Verify performance was coerced from dict
        assert props.performance.max_connections == 1000
        assert props.performance.enable_compression is True

    def test_create_service_connection_with_model_objects(self):
        """Test that model objects are passed through correctly."""
        from omnibase_core.models.connections.model_database_properties import (
            ModelDatabaseProperties,
        )
        from omnibase_core.models.connections.model_message_queue_properties import (
            ModelMessageQueueProperties,
        )
        from omnibase_core.models.connections.model_performance_properties import (
            ModelPerformanceProperties,
        )
        from omnibase_core.models.core.model_custom_properties import (
            ModelCustomProperties,
        )

        db = ModelDatabaseProperties(database_display_name="service_db")
        queue = ModelMessageQueueProperties(exchange_display_name="service_exchange")
        perf = ModelPerformanceProperties(enable_compression=True, compression_level=5)
        custom = ModelCustomProperties()
        custom.set_custom_flag("active", True)
        custom.set_custom_number("priority", 1.0)

        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="worker-service",
            database=db,
            message_queue=queue,
            performance=perf,
            custom_properties=custom,
        )

        assert props.cloud_service.service_display_name == "worker-service"
        assert props.database.database_display_name == "service_db"
        assert props.message_queue.exchange_display_name == "service_exchange"
        assert props.performance.enable_compression is True
        assert props.performance.compression_level == 5
        assert props.custom_properties.get_custom_value("active") is True
        assert props.custom_properties.get_custom_value("priority") == 1.0

    def test_create_service_connection_with_none_kwargs(self):
        """Test that None kwargs return default model instances."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            database=None,
            message_queue=None,
            performance=None,
            custom_properties=None,
        )

        assert props.cloud_service.service_display_name == "test_service"
        assert props.database.database_display_name is None
        assert props.message_queue.queue_display_name is None
        assert props.performance.max_connections == 100  # Default
        assert props.custom_properties.is_empty() is True

    def test_create_service_connection_with_invalid_kwargs(self):
        """Test that invalid kwargs return defaults (lenient mode)."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            database=set(),  # Invalid type (set is not dict-like)
            message_queue=lambda x: x,  # Invalid type (function)
            performance=True,  # Invalid type (bool)
        )

        # All should get defaults due to lenient mode
        assert props.cloud_service.service_display_name == "test_service"
        assert props.database.database_display_name is None
        assert props.message_queue.queue_display_name is None
        assert props.performance.max_connections == 100

    def test_create_service_connection_with_custom_properties_dict(self):
        """Test custom_properties kwarg with dict format."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            custom_properties={
                "custom_strings": {"env": "staging"},
                "custom_numbers": {"timeout": 30.0},
                "custom_flags": {"debug": True},
            },
        )

        assert props.custom_properties.get_custom_value("env") == "staging"
        assert props.custom_properties.get_custom_value("timeout") == 30.0
        assert props.custom_properties.get_custom_value("debug") is True

    # ==========================================================================
    # Cross-cutting coercion behavior tests
    # ==========================================================================

    def test_coercion_preserves_model_identity_check(self):
        """Test that coerced models are proper instances of their types."""
        from omnibase_core.models.connections.model_performance_properties import (
            ModelPerformanceProperties,
        )

        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test",
            performance={"max_connections": 50},
        )

        # The coerced performance should be a proper ModelPerformanceProperties
        assert isinstance(props.performance, ModelPerformanceProperties)

    def test_coercion_handles_empty_dict(self):
        """Test that empty dicts produce default model instances."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test",
            performance={},
            message_queue={},
            cloud_service={},
        )

        # Empty dicts should produce models with all defaults
        assert props.performance.max_connections == 100
        assert props.performance.enable_compression is False
        assert props.message_queue.queue_display_name is None
        assert props.cloud_service.region is None

    def test_all_factory_methods_support_all_kwargs(self):
        """Test that all factory methods accept all optional nested model kwargs."""
        # Each factory should support message_queue, cloud_service, database,
        # performance, and custom_properties (except its own primary concern)

        db_props = ModelCustomConnectionProperties.create_database_connection(
            database_name="db",
            message_queue={"queue_display_name": "q"},
            cloud_service={"region": "r"},
            performance={"max_connections": 1},
            custom_properties={"custom_strings": {"k": "v"}},
        )
        assert db_props.message_queue.queue_display_name == "q"
        assert db_props.cloud_service.region == "r"
        assert db_props.performance.max_connections == 1
        assert db_props.custom_properties.get_custom_value("k") == "v"

        queue_props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="q",
            database={"database_display_name": "db"},
            cloud_service={"region": "r"},
            performance={"max_connections": 2},
            custom_properties={"custom_numbers": {"n": 1.5}},
        )
        assert queue_props.database.database_display_name == "db"
        assert queue_props.cloud_service.region == "r"
        assert queue_props.performance.max_connections == 2
        assert queue_props.custom_properties.get_custom_value("n") == 1.5

        service_props = ModelCustomConnectionProperties.create_service_connection(
            service_name="s",
            database={"database_display_name": "db"},
            message_queue={"queue_display_name": "q"},
            performance={"max_connections": 3},
            custom_properties={"custom_flags": {"f": True}},
        )
        assert service_props.database.database_display_name == "db"
        assert service_props.message_queue.queue_display_name == "q"
        assert service_props.performance.max_connections == 3
        assert service_props.custom_properties.get_custom_value("f") is True


@pytest.mark.unit
class TestFactoryMethodsUnknownKwargs:
    """Test cases for unknown kwargs handling in factory methods.

    These tests verify that factory methods silently ignore unknown kwargs
    (kwargs that are not one of the supported nested model keys). This
    behavior is documented in the factory method docstrings.

    The supported kwargs are:
    - create_database_connection: message_queue, cloud_service, performance, custom_properties
    - create_queue_connection: database, cloud_service, performance, custom_properties
    - create_service_connection: database, message_queue, performance, custom_properties
    """

    def test_create_database_connection_ignores_unknown_kwargs(self):
        """Test that unknown kwargs are silently ignored in create_database_connection."""
        # Pass unknown kwargs that don't match any supported key
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            unknown_param="should_be_ignored",
            another_unknown=12345,
            yet_another={"nested": "value"},
        )

        # Primary properties should be set correctly
        assert props.database.database_display_name == "test_db"

        # All other nested models should have defaults (unknown kwargs ignored)
        assert props.message_queue.queue_display_name is None
        assert props.cloud_service.region is None
        assert props.performance.max_connections == 100  # Default

        # The model should not have any attributes from unknown kwargs
        # (They're silently ignored, not stored anywhere)
        assert not hasattr(props, "unknown_param")
        assert not hasattr(props, "another_unknown")
        assert not hasattr(props, "yet_another")

    def test_create_queue_connection_ignores_unknown_kwargs(self):
        """Test that unknown kwargs are silently ignored in create_queue_connection."""
        props = ModelCustomConnectionProperties.create_queue_connection(
            queue_name="test_queue",
            typo_parameter="ignored",
            invalid_key=object(),
        )

        # Primary properties should be set correctly
        assert props.message_queue.queue_display_name == "test_queue"

        # All other nested models should have defaults
        assert props.database.database_display_name is None
        assert props.cloud_service.region is None
        assert props.performance.max_connections == 100

    def test_create_service_connection_ignores_unknown_kwargs(self):
        """Test that unknown kwargs are silently ignored in create_service_connection."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service",
            region="us-west-2",
            misspelled_performance={
                "max_connections": 500
            },  # Note: should be 'performance'
            random_param=True,
        )

        # Primary properties should be set correctly
        assert props.cloud_service.service_display_name == "test_service"
        assert props.cloud_service.region == "us-west-2"

        # misspelled_performance was ignored, so performance has defaults
        assert props.performance.max_connections == 100  # Default, not 500

    def test_unknown_kwargs_mixed_with_valid_kwargs(self):
        """Test that valid kwargs work correctly when mixed with unknown kwargs."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            # Valid kwarg
            performance={"max_connections": 200},
            # Unknown kwargs (silently ignored)
            unknown_key="ignored",
            another_unknown=999,
        )

        # Valid kwargs should be processed
        assert props.database.database_display_name == "test_db"
        assert props.performance.max_connections == 200

        # Unknown kwargs should not affect the result
        assert props.message_queue.queue_display_name is None
        assert props.cloud_service.region is None

    def test_kwargs_similar_to_valid_keys_are_ignored(self):
        """Test that kwargs with names similar to valid keys are still ignored.

        This tests that typos in kwarg names are silently ignored rather than
        causing errors. Users should be aware that misspelled keys will not
        raise errors but will result in default values.
        """
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            # Typos of valid keys (all should be silently ignored)
            messagequeue={"queue_display_name": "queue"},  # Missing underscore
            cloudservice={"region": "eu-west-1"},  # Missing underscore
            Perforamnce={"max_connections": 300},  # Misspelled
            Performance={"max_connections": 400},  # Wrong capitalization
        )

        # All should have defaults because the kwargs were ignored
        assert props.database.database_display_name == "test_db"
        assert props.message_queue.queue_display_name is None
        assert props.cloud_service.region is None
        assert props.performance.max_connections == 100  # Default

    def test_empty_kwargs(self):
        """Test that factory methods work correctly with no extra kwargs."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
        )

        assert props.database.database_display_name == "test_db"
        assert props.message_queue.queue_display_name is None
        assert props.cloud_service.region is None
        assert props.performance.max_connections == 100


@pytest.mark.unit
class TestCoerceToModelHelper:
    """Test cases for the _coerce_to_model helper function behavior.

    These tests verify the duck typing coercion behavior used by factory methods.
    The helper function is tested indirectly through the factory method calls.
    """

    def test_coercion_with_valid_dict_extra_fields(self):
        """Test that dicts with extra unknown fields are handled gracefully.

        The nested model's model_config has extra='ignore', so unknown fields
        in the dict are silently ignored during coercion.
        """
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            performance={
                "max_connections": 250,
                "unknown_nested_field": "should_be_ignored",
                "another_unknown": 12345,
            },
        )

        # Known field should be set
        assert props.performance.max_connections == 250
        # Unknown fields in the dict are ignored by the nested model
        assert not hasattr(props.performance, "unknown_nested_field")
        assert not hasattr(props.performance, "another_unknown")

    def test_coercion_with_callable_returns_default(self):
        """Test that passing a callable (function) returns default instance."""
        props = ModelCustomConnectionProperties.create_database_connection(
            database_name="test_db",
            performance=lambda x: x,  # Callable is not a valid input
        )

        # Should get default instance (lenient mode)
        assert props.performance.max_connections == 100

    def test_coercion_with_complex_invalid_types(self):
        """Test coercion with various invalid types returns defaults."""

        # Test with generator
        def gen():
            yield 1

        props1 = ModelCustomConnectionProperties.create_database_connection(
            database_name="test1",
            performance=gen(),
        )
        assert props1.performance.max_connections == 100

        # Test with bytes
        props2 = ModelCustomConnectionProperties.create_database_connection(
            database_name="test2",
            performance=b"bytes_data",
        )
        assert props2.performance.max_connections == 100

        # Test with frozenset
        props3 = ModelCustomConnectionProperties.create_database_connection(
            database_name="test3",
            cloud_service=frozenset([1, 2, 3]),
        )
        assert props3.cloud_service.region is None

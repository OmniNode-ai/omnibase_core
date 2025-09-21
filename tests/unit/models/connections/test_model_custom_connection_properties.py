"""
Test module for ModelCustomConnectionProperties.

Tests the refactored connection properties model with UUID references
and backward compatibility factory methods.
"""

from uuid import UUID, uuid4

import pytest

from src.omnibase_core.enums.enum_instance_type import EnumInstanceType
from src.omnibase_core.models.connections.model_custom_connection_properties import (
    ModelCustomConnectionProperties,
)


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
            service_name="test_service", instance_type="t3.medium"
        )

        assert props.service_display_name == "test_service"
        assert props.instance_type == EnumInstanceType.T3_MEDIUM

    def test_service_connection_factory_with_generic_string(self):
        """Test creating service connection with generic string instance type."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service", instance_type="large"
        )

        assert props.service_display_name == "test_service"
        assert props.instance_type == EnumInstanceType.LARGE

    def test_service_connection_factory_with_unknown_string(self):
        """Test creating service connection with unknown string instance type."""
        props = ModelCustomConnectionProperties.create_service_connection(
            service_name="test_service", instance_type="custom_unknown_type"
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
        data = props.model_dump()
        assert data["database_display_name"] == "test_db"
        assert data["instance_type"] == "t3.medium"
        assert data["max_connections"] == 100
        assert data["enable_compression"] is True

    def test_custom_properties_integration(self):
        """Test integration with custom properties."""
        props = ModelCustomConnectionProperties(database_display_name="test_db")

        # Custom properties should be initialized
        assert props.custom_properties is not None

        # Should be able to add custom properties
        props.custom_properties.set_property("custom_key", "custom_value")
        assert props.custom_properties.get_property("custom_key") == "custom_value"

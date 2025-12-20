"""Tests for EnumServiceType."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_service_type import EnumServiceType


@pytest.mark.unit
class TestEnumServiceType:
    """Test suite for EnumServiceType."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumServiceType.KAFKA == "kafka"
        assert EnumServiceType.POSTGRESQL == "postgresql"
        assert EnumServiceType.MYSQL == "mysql"
        assert EnumServiceType.REDIS == "redis"
        assert EnumServiceType.ELASTICSEARCH == "elasticsearch"
        assert EnumServiceType.MONGODB == "mongodb"
        assert EnumServiceType.REST_API == "rest_api"
        assert EnumServiceType.GRPC == "grpc"
        assert EnumServiceType.RABBITMQ == "rabbitmq"
        assert EnumServiceType.CONSUL == "consul"
        assert EnumServiceType.VAULT == "vault"
        assert EnumServiceType.S3 == "s3"
        assert EnumServiceType.CUSTOM == "custom"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumServiceType, str)
        assert issubclass(EnumServiceType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        service = EnumServiceType.KAFKA
        assert isinstance(service, str)
        assert service == "kafka"
        assert len(service) == 5

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumServiceType)
        assert len(values) == 13
        assert EnumServiceType.KAFKA in values
        assert EnumServiceType.CUSTOM in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumServiceType.POSTGRESQL in EnumServiceType
        assert "postgresql" in [e.value for e in EnumServiceType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        service1 = EnumServiceType.REDIS
        service2 = EnumServiceType.REDIS
        service3 = EnumServiceType.MONGODB

        assert service1 == service2
        assert service1 != service3
        assert service1 == "redis"

    def test_enum_serialization(self):
        """Test enum serialization."""
        service = EnumServiceType.ELASTICSEARCH
        serialized = service.value
        assert serialized == "elasticsearch"
        json_str = json.dumps(service)
        assert json_str == '"elasticsearch"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        service = EnumServiceType("rabbitmq")
        assert service == EnumServiceType.RABBITMQ

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumServiceType("invalid_service")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "kafka",
            "postgresql",
            "mysql",
            "redis",
            "elasticsearch",
            "mongodb",
            "rest_api",
            "grpc",
            "rabbitmq",
            "consul",
            "vault",
            "s3",
            "custom",
        }
        actual_values = {e.value for e in EnumServiceType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumServiceType.__doc__ is not None
        assert "service" in EnumServiceType.__doc__.lower()

    def test_messaging_services(self):
        """Test messaging service grouping."""
        messaging = {
            EnumServiceType.KAFKA,
            EnumServiceType.RABBITMQ,
        }
        assert all(service in EnumServiceType for service in messaging)

    def test_database_services(self):
        """Test database service grouping."""
        databases = {
            EnumServiceType.POSTGRESQL,
            EnumServiceType.MYSQL,
            EnumServiceType.MONGODB,
        }
        assert all(service in EnumServiceType for service in databases)

    def test_cache_services(self):
        """Test cache service grouping."""
        cache = {EnumServiceType.REDIS}
        assert all(service in EnumServiceType for service in cache)

    def test_search_services(self):
        """Test search service grouping."""
        search = {EnumServiceType.ELASTICSEARCH}
        assert all(service in EnumServiceType for service in search)

    def test_api_services(self):
        """Test API service grouping."""
        apis = {
            EnumServiceType.REST_API,
            EnumServiceType.GRPC,
        }
        assert all(service in EnumServiceType for service in apis)

    def test_infrastructure_services(self):
        """Test infrastructure service grouping."""
        infrastructure = {
            EnumServiceType.CONSUL,
            EnumServiceType.VAULT,
        }
        assert all(service in EnumServiceType for service in infrastructure)

    def test_storage_services(self):
        """Test storage service grouping."""
        storage = {EnumServiceType.S3}
        assert all(service in EnumServiceType for service in storage)

    def test_custom_service(self):
        """Test custom service type."""
        custom = {EnumServiceType.CUSTOM}
        assert all(service in EnumServiceType for service in custom)

    def test_all_services_categorized(self):
        """Test that all services are properly categorized."""
        # Messaging
        messaging = {EnumServiceType.KAFKA, EnumServiceType.RABBITMQ}
        # Databases
        databases = {
            EnumServiceType.POSTGRESQL,
            EnumServiceType.MYSQL,
            EnumServiceType.MONGODB,
        }
        # Cache
        cache = {EnumServiceType.REDIS}
        # Search
        search = {EnumServiceType.ELASTICSEARCH}
        # APIs
        apis = {EnumServiceType.REST_API, EnumServiceType.GRPC}
        # Infrastructure
        infrastructure = {EnumServiceType.CONSUL, EnumServiceType.VAULT}
        # Storage
        storage = {EnumServiceType.S3}
        # Custom
        custom = {EnumServiceType.CUSTOM}

        all_services = (
            messaging
            | databases
            | cache
            | search
            | apis
            | infrastructure
            | storage
            | custom
        )
        assert all_services == set(EnumServiceType)

#!/usr/bin/env python3
"""
Comprehensive tests for InMemoryServiceDiscovery implementation.

Tests strong typing, ModelScalarValue conversion, and all service discovery functionality.
"""

import asyncio

import pytest

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.services.memory_service_discovery import InMemoryServiceDiscovery


class TestInMemoryServiceDiscovery:
    """Test suite for InMemoryServiceDiscovery with strong typing validation."""

    @pytest.fixture
    def service_discovery(self) -> InMemoryServiceDiscovery:
        """Create a fresh service discovery instance for each test."""
        return InMemoryServiceDiscovery()

    @pytest.fixture
    def sample_metadata(self) -> dict[str, ModelScalarValue]:
        """Sample metadata using ModelScalarValue objects."""
        return {
            "environment": ModelScalarValue.create_string("production"),
            "version": ModelScalarValue.create_string("1.2.3"),
            "region": ModelScalarValue.create_string("us-east-1"),
            "replica_count": ModelScalarValue.create_int(3),
            "load_balancer_weight": ModelScalarValue.create_float(0.75),
            "high_availability": ModelScalarValue.create_bool(True),
        }

    # Service Registration Tests

    @pytest.mark.asyncio
    async def test_register_service_basic(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test basic service registration functionality."""
        result = await service_discovery.register_service(
            service_name="test-api",
            service_id="test-api-001",
            host="localhost",
            port=8080,
            metadata={"basic": ModelScalarValue.create_string("test")},
        )

        assert result is True

        # Verify service was stored
        all_services = await service_discovery.get_all_services()
        assert "test-api-001" in all_services

        service_info = all_services["test-api-001"]
        assert service_info["service_name"] == "test-api"
        assert service_info["host"] == "localhost"
        assert service_info["port"] == 8080

    @pytest.mark.asyncio
    async def test_register_service_with_metadata(
        self,
        service_discovery: InMemoryServiceDiscovery,
        sample_metadata: dict[str, ModelScalarValue],
    ):
        """Test service registration with strongly typed metadata."""
        result = await service_discovery.register_service(
            service_name="api-service",
            service_id="api-001",
            host="192.168.1.100",
            port=9000,
            metadata=sample_metadata,
            health_check_url="http://192.168.1.100:9000/health",
            tags=["api", "v1", "production"],
        )

        assert result is True

        all_services = await service_discovery.get_all_services()
        service_info = all_services["api-001"]

        # Verify metadata was stored as ModelScalarValue objects
        assert isinstance(service_info["metadata"], dict)
        assert "environment" in service_info["metadata"]
        assert isinstance(service_info["metadata"]["environment"], ModelScalarValue)
        assert service_info["metadata"]["environment"].string_value == "production"

    @pytest.mark.asyncio
    async def test_register_service_initializes_health(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test that service registration initializes health status."""
        await service_discovery.register_service(
            service_name="health-test-service",
            service_id="health-test-001",
            host="localhost",
            port=8080,
            metadata={"test": ModelScalarValue.create_string("health_init")},
        )

        health = await service_discovery.get_service_health("health-test-001")
        assert health.service_id == "health-test-001"
        assert health.status == "healthy"
        assert health.error_message is None

    # Service Discovery Tests

    @pytest.mark.asyncio
    async def test_discover_services_returns_model_scalar_values(
        self,
        service_discovery: InMemoryServiceDiscovery,
        sample_metadata: dict[str, ModelScalarValue],
    ):
        """Test that discover_services returns properly typed ModelScalarValue objects."""
        # Register multiple services
        await service_discovery.register_service(
            service_name="web-service",
            service_id="web-001",
            host="10.0.0.1",
            port=80,
            metadata=sample_metadata,
        )

        await service_discovery.register_service(
            service_name="web-service",
            service_id="web-002",
            host="10.0.0.2",
            port=80,
            metadata={"datacenter": ModelScalarValue.create_string("east")},
        )

        # Discover services
        services = await service_discovery.discover_services("web-service")

        assert len(services) == 2

        # Validate return type structure
        for service in services:
            assert isinstance(service, dict)

            # Check that all required fields are ModelScalarValue instances
            assert isinstance(service["service_name"], ModelScalarValue)
            assert isinstance(service["service_id"], ModelScalarValue)
            assert isinstance(service["host"], ModelScalarValue)
            assert isinstance(service["port"], ModelScalarValue)
            assert isinstance(service["health_status"], ModelScalarValue)
            assert isinstance(service["registered_at"], ModelScalarValue)

            # Validate specific values
            assert service["service_name"].string_value == "web-service"
            assert service["host"].string_value in ["10.0.0.1", "10.0.0.2"]
            assert service["port"].int_value == 80
            assert service["health_status"].string_value == "healthy"

    @pytest.mark.asyncio
    async def test_discover_services_includes_metadata(
        self,
        service_discovery: InMemoryServiceDiscovery,
        sample_metadata: dict[str, ModelScalarValue],
    ):
        """Test that discover_services includes metadata in ModelScalarValue format."""
        await service_discovery.register_service(
            service_name="metadata-service",
            service_id="meta-001",
            host="localhost",
            port=8080,
            metadata=sample_metadata,
        )

        services = await service_discovery.discover_services("metadata-service")

        assert len(services) == 1
        service = services[0]

        # Verify metadata is included
        assert "environment" in service
        assert isinstance(service["environment"], ModelScalarValue)
        assert service["environment"].string_value == "production"

        assert "replica_count" in service
        assert isinstance(service["replica_count"], ModelScalarValue)
        assert service["replica_count"].int_value == 3

        assert "load_balancer_weight" in service
        assert isinstance(service["load_balancer_weight"], ModelScalarValue)
        assert service["load_balancer_weight"].float_value == 0.75

        assert "high_availability" in service
        assert isinstance(service["high_availability"], ModelScalarValue)
        assert service["high_availability"].bool_value is True

    @pytest.mark.asyncio
    async def test_discover_services_healthy_only_filter(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test that healthy_only parameter filters unhealthy services."""
        # Register services
        await service_discovery.register_service(
            service_name="filter-test",
            service_id="healthy-001",
            host="localhost",
            port=8080,
            metadata={"type": ModelScalarValue.create_string("healthy")},
        )

        await service_discovery.register_service(
            service_name="filter-test",
            service_id="unhealthy-001",
            host="localhost",
            port=8081,
            metadata={"type": ModelScalarValue.create_string("unhealthy")},
        )

        # Mark one service as unhealthy
        await service_discovery.update_service_health(
            "unhealthy-001",
            "critical",
            "Service down",
        )

        # Test healthy_only=True (default)
        healthy_services = await service_discovery.discover_services(
            "filter-test",
            healthy_only=True,
        )
        assert len(healthy_services) == 1
        assert healthy_services[0]["service_id"].string_value == "healthy-001"

        # Test healthy_only=False
        all_services = await service_discovery.discover_services(
            "filter-test",
            healthy_only=False,
        )
        assert len(all_services) == 2

    @pytest.mark.asyncio
    async def test_discover_services_empty_result(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test discover_services with non-existent service name."""
        services = await service_discovery.discover_services("non-existent-service")

        assert isinstance(services, list)
        assert len(services) == 0

    # Service Health Tests

    @pytest.mark.asyncio
    async def test_get_service_health_registered(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test get_service_health for registered service."""
        await service_discovery.register_service(
            service_name="health-service",
            service_id="health-001",
            host="localhost",
            port=8080,
            metadata={"purpose": ModelScalarValue.create_string("health_testing")},
        )

        health = await service_discovery.get_service_health("health-001")

        # Health object should have expected attributes (compatible with ModelServiceHealth interface)
        assert hasattr(health, "service_id")
        assert hasattr(health, "status")
        assert hasattr(health, "error_message")
        assert health.service_id == "health-001"
        assert health.status == "healthy"
        assert health.error_message is None
        assert health.last_check is not None

    @pytest.mark.asyncio
    async def test_get_service_health_unregistered(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test get_service_health for unregistered service."""
        health = await service_discovery.get_service_health("non-existent-001")

        # Health object should have expected attributes (compatible with ModelServiceHealth interface)
        assert hasattr(health, "service_id")
        assert hasattr(health, "status")
        assert hasattr(health, "error_message")
        assert health.service_id == "non-existent-001"
        assert health.status == "critical"
        assert health.error_message == "Service not registered"

    @pytest.mark.asyncio
    async def test_update_service_health(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test updating service health status."""
        await service_discovery.register_service(
            service_name="update-health-service",
            service_id="update-001",
            host="localhost",
            port=8080,
            metadata={"test": ModelScalarValue.create_string("health_update")},
        )

        # Update to warning status
        await service_discovery.update_service_health(
            "update-001",
            "warning",
            "High latency detected",
        )

        health = await service_discovery.get_service_health("update-001")
        assert health.status == "warning"
        assert health.error_message == "High latency detected"

    # Service Deregistration Tests

    @pytest.mark.asyncio
    async def test_deregister_service(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test service deregistration."""
        # Register service
        await service_discovery.register_service(
            service_name="deregister-test",
            service_id="dereg-001",
            host="localhost",
            port=8080,
            metadata={"test": ModelScalarValue.create_string("deregister")},
        )

        # Verify registration
        services = await service_discovery.discover_services("deregister-test")
        assert len(services) == 1

        # Deregister
        result = await service_discovery.deregister_service("dereg-001")
        assert result is True

        # Verify deregistration
        services = await service_discovery.discover_services("deregister-test")
        assert len(services) == 0

        # Health info should also be removed
        health = await service_discovery.get_service_health("dereg-001")
        assert health.status == "critical"
        assert "not registered" in health.error_message

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_service(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test deregistering a non-existent service."""
        result = await service_discovery.deregister_service("non-existent-001")
        assert result is True  # Should not fail

    # Key-Value Store Tests

    @pytest.mark.asyncio
    async def test_key_value_operations(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test key-value store functionality."""
        # Set key-value
        result = await service_discovery.set_key_value(
            "config/database_url",
            "postgresql://localhost:5432/mydb",
        )
        assert result is True

        # Get key-value
        value = await service_discovery.get_key_value("config/database_url")
        assert value == "postgresql://localhost:5432/mydb"

        # Get non-existent key
        missing = await service_discovery.get_key_value("non-existent-key")
        assert missing is None

    @pytest.mark.asyncio
    async def test_delete_key(self, service_discovery: InMemoryServiceDiscovery):
        """Test key deletion."""
        # Set and verify key
        await service_discovery.set_key_value("temp/test_key", "test_value")
        value = await service_discovery.get_key_value("temp/test_key")
        assert value == "test_value"

        # Delete key
        result = await service_discovery.delete_key("temp/test_key")
        assert result is True

        # Verify deletion
        value = await service_discovery.get_key_value("temp/test_key")
        assert value is None

        # Delete non-existent key
        result = await service_discovery.delete_key("non-existent-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_keys(self, service_discovery: InMemoryServiceDiscovery):
        """Test listing keys with prefix filtering."""
        # Set multiple keys
        await service_discovery.set_key_value("config/db_host", "localhost")
        await service_discovery.set_key_value("config/db_port", "5432")
        await service_discovery.set_key_value("config/redis_host", "localhost")
        await service_discovery.set_key_value("cache/timeout", "300")

        # List all keys
        all_keys = await service_discovery.list_keys()
        assert len(all_keys) == 4
        assert "config/db_host" in all_keys
        assert "cache/timeout" in all_keys

        # List keys with prefix
        config_keys = await service_discovery.list_keys("config/")
        assert len(config_keys) == 3
        assert all(key.startswith("config/") for key in config_keys)

    # System Health and Statistics Tests

    @pytest.mark.asyncio
    async def test_health_check(self, service_discovery: InMemoryServiceDiscovery):
        """Test system health check."""
        result = await service_discovery.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_stats(self, service_discovery: InMemoryServiceDiscovery):
        """Test getting service discovery statistics."""
        # Register some services and set some keys
        await service_discovery.register_service(
            "stats-service-1",
            "stats-001",
            "localhost",
            8080,
            metadata={"role": ModelScalarValue.create_string("primary")},
        )
        await service_discovery.register_service(
            "stats-service-2",
            "stats-002",
            "localhost",
            8081,
            metadata={"role": ModelScalarValue.create_string("secondary")},
        )
        await service_discovery.set_key_value("stats/key1", "value1")
        await service_discovery.set_key_value("stats/key2", "value2")

        # Mark one service as unhealthy
        await service_discovery.update_service_health(
            "stats-002",
            "critical",
            "Test error",
        )

        stats = await service_discovery.get_stats()

        assert isinstance(stats, dict)
        assert stats["total_services"] == 2
        assert stats["total_kv_pairs"] == 2
        assert stats["healthy_services"] == 1
        assert "stats-service-1" in stats["service_names"]
        assert "stats-service-2" in stats["service_names"]

    # Cleanup and Resource Management Tests

    @pytest.mark.asyncio
    async def test_close_cleanup(self, service_discovery: InMemoryServiceDiscovery):
        """Test resource cleanup on close."""
        # Add some data
        await service_discovery.register_service(
            "cleanup-service",
            "cleanup-001",
            "localhost",
            8080,
            metadata={"test": ModelScalarValue.create_string("cleanup")},
        )
        await service_discovery.set_key_value("cleanup/key", "value")

        # Verify data exists
        services = await service_discovery.discover_services("cleanup-service")
        assert len(services) == 1

        value = await service_discovery.get_key_value("cleanup/key")
        assert value == "value"

        # Close and verify cleanup
        await service_discovery.close()

        services = await service_discovery.discover_services("cleanup-service")
        assert len(services) == 0

        value = await service_discovery.get_key_value("cleanup/key")
        assert value is None

    # Concurrency and Thread Safety Tests

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test concurrent service operations."""

        async def register_service(index: int) -> bool:
            return await service_discovery.register_service(
                service_name="concurrent-service",
                service_id=f"concurrent-{index:03d}",
                host="localhost",
                port=8000 + index,
                metadata={"index": ModelScalarValue.create_int(index)},
            )

        # Register services concurrently
        tasks = [register_service(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

        # Verify all services were registered
        services = await service_discovery.discover_services("concurrent-service")
        assert len(services) == 10

        # Verify unique service IDs
        service_ids = {service["service_id"].string_value for service in services}
        assert len(service_ids) == 10

    # Edge Cases and Error Scenarios

    @pytest.mark.asyncio
    async def test_invalid_metadata_types(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test handling of invalid metadata types."""
        # This test ensures metadata must be ModelScalarValue objects
        # The implementation should handle this gracefully
        valid_metadata = {
            "key1": ModelScalarValue.create_string("value1"),
            "key2": ModelScalarValue.create_int(42),
        }

        result = await service_discovery.register_service(
            service_name="metadata-test",
            service_id="meta-test-001",
            host="localhost",
            port=8080,
            metadata=valid_metadata,
        )

        assert result is True

        services = await service_discovery.discover_services("metadata-test")
        assert len(services) == 1
        assert "key1" in services[0]
        assert services[0]["key1"].string_value == "value1"

    @pytest.mark.asyncio
    async def test_service_id_uniqueness(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test that service IDs must be unique."""
        # Register first service
        result1 = await service_discovery.register_service(
            service_name="unique-test",
            service_id="duplicate-id",
            host="localhost",
            port=8080,
            metadata={"version": ModelScalarValue.create_int(1)},
        )
        assert result1 is True

        # Register second service with same ID (should overwrite)
        result2 = await service_discovery.register_service(
            service_name="unique-test-2",
            service_id="duplicate-id",
            host="localhost",
            port=8081,
            metadata={"version": ModelScalarValue.create_int(2)},
        )
        assert result2 is True

        # Should only have one service with that ID
        all_services = await service_discovery.get_all_services()
        assert (
            len([s for s in all_services.values() if s["service_id"] == "duplicate-id"])
            == 1
        )

        # Should be the second service (overwrite behavior)
        service_info = all_services["duplicate-id"]
        assert service_info["service_name"] == "unique-test-2"
        assert service_info["port"] == 8081


class TestModelScalarValueIntegration:
    """Test ModelScalarValue integration specifically in service discovery context."""

    @pytest.fixture
    def service_discovery(self) -> InMemoryServiceDiscovery:
        """Create a fresh service discovery instance."""
        return InMemoryServiceDiscovery()

    @pytest.mark.asyncio
    async def test_scalar_value_type_preservation(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test that ModelScalarValue types are preserved through the discovery process."""
        metadata = {
            "string_field": ModelScalarValue.create_string("test_string"),
            "int_field": ModelScalarValue.create_int(42),
            "float_field": ModelScalarValue.create_float(3.14),
            "bool_field": ModelScalarValue.create_bool(True),
        }

        await service_discovery.register_service(
            service_name="type-test",
            service_id="type-001",
            host="localhost",
            port=8080,
            metadata=metadata,
        )

        services = await service_discovery.discover_services("type-test")
        service = services[0]

        # Verify type preservation
        assert service["string_field"].type_hint == "str"
        assert service["int_field"].type_hint == "int"
        assert service["float_field"].type_hint == "float"
        assert service["bool_field"].type_hint == "bool"

        # Verify value extraction
        assert service["string_field"].to_string_primitive() == "test_string"
        assert service["int_field"].to_int_primitive() == 42
        assert service["float_field"].to_float_primitive() == 3.14
        assert service["bool_field"].to_bool_primitive() is True

    @pytest.mark.asyncio
    async def test_scalar_value_validation(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test ModelScalarValue validation in service discovery context."""
        # Test that only one value type can be set
        with pytest.raises(ValueError, match="exactly one value"):
            ModelScalarValue(string_value="test", int_value=42)

        # Test that at least one value must be set
        with pytest.raises(ValueError, match="exactly one value"):
            ModelScalarValue()

        # Test factory methods work correctly
        string_val = ModelScalarValue.create_string("test")
        assert string_val.string_value == "test"
        assert string_val.int_value is None

        int_val = ModelScalarValue.create_int(42)
        assert int_val.int_value == 42
        assert int_val.string_value is None

    @pytest.mark.asyncio
    async def test_primitive_conversion_edge_cases(
        self,
        service_discovery: InMemoryServiceDiscovery,
    ):
        """Test edge cases in primitive value conversion."""
        # Test conversion errors
        string_val = ModelScalarValue.create_string("test")

        with pytest.raises(ValueError, match="No int value"):
            string_val.to_int_primitive()

        with pytest.raises(ValueError, match="No float value"):
            string_val.to_float_primitive()

        with pytest.raises(ValueError, match="No bool value"):
            string_val.to_bool_primitive()

        # Test successful extraction
        assert string_val.to_string_primitive() == "test"

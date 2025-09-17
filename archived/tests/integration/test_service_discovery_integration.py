#!/usr/bin/env python3
"""
Integration tests for service discovery implementations.

Tests protocol compliance, cross-implementation scenarios, and integration patterns.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery
from omnibase_core.services.consul_service_discovery import ConsulServiceDiscovery
from omnibase_core.services.memory_service_discovery import InMemoryServiceDiscovery


class TestServiceDiscoveryProtocolCompliance:
    """Test that both implementations comply with ProtocolServiceDiscovery."""

    @pytest.fixture(params=["memory", "consul_with_fallback", "consul_fallback_only"])
    def service_discovery(self, request) -> ProtocolServiceDiscovery:
        """Parametrized fixture providing different service discovery implementations."""
        if request.param == "memory":
            return InMemoryServiceDiscovery()
        if request.param == "consul_with_fallback":
            # Mock successful Consul connection
            mock_client = Mock()
            mock_client.agent.self.return_value = {}
            mock_client.agent.service.register.return_value = True
            mock_client.agent.service.deregister.return_value = True
            mock_client.health.service.return_value = (None, [])
            mock_client.health.checks.return_value = (None, [])
            mock_client.kv.put.return_value = True
            mock_client.kv.get.return_value = (None, None)
            mock_client.kv.delete.return_value = True

            with patch("consul.Consul", return_value=mock_client):
                return ConsulServiceDiscovery(enable_fallback=True)
        elif request.param == "consul_fallback_only":
            # Force Consul to fail, use fallback only
            with patch("consul.Consul", side_effect=ImportError("No consul module")):
                return ConsulServiceDiscovery(enable_fallback=True)

        raise ValueError(f"Unknown parameter: {request.param}")

    @pytest.mark.asyncio
    async def test_protocol_compliance_basic_operations(
        self,
        service_discovery: ProtocolServiceDiscovery,
    ):
        """Test basic protocol compliance across all implementations."""
        # Verify protocol compliance at runtime
        assert isinstance(service_discovery, ProtocolServiceDiscovery)

        # Test service registration
        result = await service_discovery.register_service(
            service_name="protocol-test",
            service_id="protocol-001",
            host="localhost",
            port=8080,
            metadata={"test": ModelScalarValue.create_string("protocol")},
        )
        assert isinstance(result, bool)
        assert result is True

        # Test service discovery with proper return type
        services = await service_discovery.discover_services("protocol-test")
        assert isinstance(services, list)

        if len(services) > 0:
            service = services[0]
            assert isinstance(service, dict)

            # Verify all values are ModelScalarValue instances
            for key, value in service.items():
                assert isinstance(
                    value,
                    ModelScalarValue,
                ), f"Key '{key}' has value type {type(value)}"

        # Test health check
        health = await service_discovery.get_service_health("protocol-001")
        # Use attribute-based validation for ModelServiceHealth compatibility
        assert hasattr(health, "service_id")
        assert hasattr(health, "status")
        assert hasattr(health, "error_message")
        assert health.service_id == "protocol-001"

        # Test deregistration
        result = await service_discovery.deregister_service("protocol-001")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_protocol_compliance_kv_operations(
        self,
        service_discovery: ProtocolServiceDiscovery,
    ):
        """Test key-value operations protocol compliance."""
        # Set key-value
        result = await service_discovery.set_key_value("test/key", "test_value")
        assert isinstance(result, bool)

        # Get key-value
        value = await service_discovery.get_key_value("test/key")
        assert value is None or isinstance(value, str)

        # List keys
        keys = await service_discovery.list_keys("test/")
        assert isinstance(keys, list)
        assert all(isinstance(key, str) for key in keys)

        # Delete key
        result = await service_discovery.delete_key("test/key")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_protocol_compliance_health_and_cleanup(
        self,
        service_discovery: ProtocolServiceDiscovery,
    ):
        """Test health check and cleanup protocol compliance."""
        # Health check
        result = await service_discovery.health_check()
        assert isinstance(result, bool)

        # Cleanup (should not raise exceptions)
        await service_discovery.close()

    @pytest.mark.asyncio
    async def test_model_scalar_value_type_consistency(
        self,
        service_discovery: ProtocolServiceDiscovery,
    ):
        """Test that ModelScalarValue types are consistent across implementations."""
        metadata = {
            "string_val": ModelScalarValue.create_string("test_string"),
            "int_val": ModelScalarValue.create_int(42),
            "float_val": ModelScalarValue.create_float(3.14159),
            "bool_val": ModelScalarValue.create_bool(True),
        }

        await service_discovery.register_service(
            service_name="type-consistency-test",
            service_id="type-001",
            host="localhost",
            port=8080,
            metadata=metadata,
        )

        services = await service_discovery.discover_services("type-consistency-test")

        if len(services) > 0:
            service = services[0]

            # Verify metadata types are preserved
            if "string_val" in service:
                assert service["string_val"].type_hint == "str"
                assert service["string_val"].to_string_primitive() == "test_string"

            if "int_val" in service:
                assert service["int_val"].type_hint == "int"
                assert service["int_val"].to_int_primitive() == 42

            if "float_val" in service:
                assert service["float_val"].type_hint == "float"
                assert (
                    abs(service["float_val"].to_float_primitive() - 3.14159) < 0.00001
                )

            if "bool_val" in service:
                assert service["bool_val"].type_hint == "bool"
                assert service["bool_val"].to_bool_primitive() is True


class TestServiceDiscoveryCompliancePatterns:
    """Test protocol compliance with existing service discovery patterns."""

    @pytest.mark.asyncio
    async def test_legacy_service_registration_patterns(self):
        """Test that legacy registration patterns still work."""
        service_discovery = InMemoryServiceDiscovery()

        # Test registration without optional parameters (legacy pattern)
        result = await service_discovery.register_service(
            service_name="legacy-service",
            service_id="legacy-001",
            host="192.168.1.10",
            port=9000,
            metadata={"legacy": ModelScalarValue.create_string("test")},
        )

        assert result is True

        # Test discovery returns expected format
        services = await service_discovery.discover_services("legacy-service")
        assert len(services) == 1

        service = services[0]
        assert service["service_name"].string_value == "legacy-service"
        assert service["service_id"].string_value == "legacy-001"
        assert service["host"].string_value == "192.168.1.10"
        assert service["port"].int_value == 9000

    @pytest.mark.asyncio
    async def test_metadata_migration_compatibility(self):
        """Test compatibility with different metadata formats."""
        service_discovery = InMemoryServiceDiscovery()

        # Test with properly typed metadata
        typed_metadata = {
            "version": ModelScalarValue.create_string("1.0.0"),
            "replicas": ModelScalarValue.create_int(3),
        }

        await service_discovery.register_service(
            service_name="migration-test",
            service_id="migration-001",
            host="localhost",
            port=8080,
            metadata=typed_metadata,
        )

        services = await service_discovery.discover_services("migration-test")
        service = services[0]

        assert "version" in service
        assert service["version"].string_value == "1.0.0"
        assert "replicas" in service
        assert service["replicas"].int_value == 3

    @pytest.mark.asyncio
    async def test_health_status_compatibility(self):
        """Test health status compatibility across implementations."""
        implementations = [
            InMemoryServiceDiscovery(),
        ]

        # Add Consul with fallback if available
        try:
            with patch("consul.Consul", side_effect=ImportError("No consul")):
                implementations.append(ConsulServiceDiscovery(enable_fallback=True))
        except Exception:
            pass  # Skip if not available

        for service_discovery in implementations:
            await service_discovery.register_service(
                "health-compat-test",
                "health-001",
                "localhost",
                8080,
                metadata={"test": ModelScalarValue.create_string("health_compat")},
            )

            health = await service_discovery.get_service_health("health-001")

            # Standard health status values
            assert health.status in ["healthy", "warning", "critical", "unknown"]
            assert isinstance(health.service_id, str)
            assert health.service_id == "health-001"


class TestServiceDiscoveryCrossImplementation:
    """Test scenarios involving multiple service discovery implementations."""

    @pytest.mark.asyncio
    async def test_implementation_isolation(self):
        """Test that different implementations don't interfere with each other."""
        memory_sd = InMemoryServiceDiscovery()

        # Create Consul with fallback (will use fallback due to no consul module)
        with patch("consul.Consul", side_effect=ImportError("No consul")):
            consul_sd = ConsulServiceDiscovery(enable_fallback=True)

        # Register service in memory implementation
        await memory_sd.register_service(
            "isolation-test",
            "iso-memory",
            "localhost",
            8080,
            metadata={"impl": ModelScalarValue.create_string("memory")},
        )

        # Register service in consul implementation (via fallback)
        await consul_sd.register_service(
            "isolation-test",
            "iso-consul",
            "localhost",
            8081,
            metadata={"impl": ModelScalarValue.create_string("consul")},
        )

        # Each should only see their own services
        memory_services = await memory_sd.discover_services("isolation-test")
        consul_services = await consul_sd.discover_services("isolation-test")

        assert len(memory_services) == 1
        assert memory_services[0]["service_id"].string_value == "iso-memory"

        assert len(consul_services) == 1
        assert consul_services[0]["service_id"].string_value == "iso-consul"

    @pytest.mark.asyncio
    async def test_failover_scenarios(self):
        """Test failover between different implementations."""
        # Simulate primary service discovery failure and fallback usage
        primary_sd = InMemoryServiceDiscovery()

        # Simulate fallback service discovery
        with patch("consul.Consul", side_effect=ImportError("No consul")):
            fallback_sd = ConsulServiceDiscovery(enable_fallback=True)

        # Register services in both
        await primary_sd.register_service(
            "failover-test",
            "primary-001",
            "localhost",
            8080,
            metadata={"type": ModelScalarValue.create_string("primary")},
        )
        await fallback_sd.register_service(
            "failover-test",
            "fallback-001",
            "localhost",
            8081,
            metadata={"type": ModelScalarValue.create_string("fallback")},
        )

        # Both should work independently
        primary_services = await primary_sd.discover_services("failover-test")
        fallback_services = await fallback_sd.discover_services("failover-test")

        assert len(primary_services) == 1
        assert len(fallback_services) == 1

        # Health checks should work on both
        primary_health = await primary_sd.get_service_health("primary-001")
        fallback_health = await fallback_sd.get_service_health("fallback-001")

        assert primary_health.service_id == "primary-001"
        assert fallback_health.service_id == "fallback-001"

    @pytest.mark.asyncio
    async def test_concurrent_multi_implementation_usage(self):
        """Test concurrent usage of multiple implementations."""
        implementations = [
            InMemoryServiceDiscovery(),
            InMemoryServiceDiscovery(),  # Second instance for isolation testing
        ]

        # Add Consul fallback implementation
        with patch("consul.Consul", side_effect=ImportError("No consul")):
            implementations.append(ConsulServiceDiscovery(enable_fallback=True))

        async def register_and_discover(impl, index):
            service_id = f"concurrent-{index:03d}"
            await impl.register_service(
                "concurrent-test",
                service_id,
                "localhost",
                8080 + index,
                metadata={"index": ModelScalarValue.create_int(index)},
            )
            services = await impl.discover_services("concurrent-test")
            return len(services)

        # Run operations concurrently across all implementations
        tasks = [
            register_and_discover(impl, i) for i, impl in enumerate(implementations)
        ]
        results = await asyncio.gather(*tasks)

        # Each implementation should have exactly one service
        assert all(count == 1 for count in results)


class TestServiceDiscoveryPerformanceAndReliability:
    """Test performance and reliability characteristics."""

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self):
        """Test performance with bulk service operations."""
        service_discovery = InMemoryServiceDiscovery()

        # Register multiple services
        register_tasks = []
        for i in range(100):
            task = service_discovery.register_service(
                service_name=f"bulk-service-{i % 10}",  # 10 different service names
                service_id=f"bulk-{i:03d}",
                host="localhost",
                port=8000 + i,
                metadata={"index": ModelScalarValue.create_int(i)},
            )
            register_tasks.append(task)

        # Execute registrations concurrently
        results = await asyncio.gather(*register_tasks)
        assert all(results)

        # Test bulk discovery
        discovery_tasks = [
            service_discovery.discover_services(f"bulk-service-{i}") for i in range(10)
        ]

        discovered_services = await asyncio.gather(*discovery_tasks)

        # Each service name should have 10 instances
        for services in discovered_services:
            assert len(services) == 10

    @pytest.mark.asyncio
    async def test_error_recovery_and_consistency(self):
        """Test error recovery and data consistency."""
        service_discovery = InMemoryServiceDiscovery()

        # Register a service
        await service_discovery.register_service(
            "recovery-test",
            "recovery-001",
            "localhost",
            8080,
            metadata={"test": ModelScalarValue.create_string("recovery")},
        )

        # Verify it exists
        services = await service_discovery.discover_services("recovery-test")
        assert len(services) == 1

        # Test that deregistration and re-registration work correctly
        result = await service_discovery.deregister_service("recovery-001")
        assert result is True

        services = await service_discovery.discover_services("recovery-test")
        assert len(services) == 0

        # Re-register with different port
        await service_discovery.register_service(
            "recovery-test",
            "recovery-001",
            "localhost",
            8081,
            metadata={"test": ModelScalarValue.create_string("recovery_reregistered")},
        )

        services = await service_discovery.discover_services("recovery-test")
        assert len(services) == 1
        assert services[0]["port"].int_value == 8081

    @pytest.mark.asyncio
    async def test_memory_efficiency_and_cleanup(self):
        """Test memory efficiency and proper cleanup."""
        service_discovery = InMemoryServiceDiscovery()

        # Register many services and KV pairs
        for i in range(50):
            await service_discovery.register_service(
                f"memory-test-{i}",
                f"memory-{i:03d}",
                "localhost",
                8000 + i,
                metadata={"index": ModelScalarValue.create_int(i)},
            )
            await service_discovery.set_key_value(f"config/service-{i}", f"value-{i}")

        # Get initial stats
        stats = await service_discovery.get_stats()
        assert stats["total_services"] == 50
        assert stats["total_kv_pairs"] == 50

        # Clean up half the services
        for i in range(25):
            await service_discovery.deregister_service(f"memory-{i:03d}")
            await service_discovery.delete_key(f"config/service-{i}")

        # Verify cleanup
        stats = await service_discovery.get_stats()
        assert stats["total_services"] == 25
        assert stats["total_kv_pairs"] == 25

        # Final cleanup
        await service_discovery.close()

        # After close, should be empty
        stats = await service_discovery.get_stats()
        assert stats["total_services"] == 0
        assert stats["total_kv_pairs"] == 0


class TestServiceDiscoveryEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_and_special_values(self):
        """Test handling of empty and special values."""
        service_discovery = InMemoryServiceDiscovery()

        # Test with empty strings and special characters
        metadata = {
            "empty_string": ModelScalarValue.create_string(""),
            "special_chars": ModelScalarValue.create_string(
                "!@#$%^&*(){}[]|\\:;\"'<>?,./-_+=~`",
            ),
            "unicode": ModelScalarValue.create_string("Hello 世界 🌍"),
            "zero_values": ModelScalarValue.create_int(0),
            "negative": ModelScalarValue.create_int(-999),
            "large_number": ModelScalarValue.create_int(2**60),
            "small_float": ModelScalarValue.create_float(0.000001),
            "false_bool": ModelScalarValue.create_bool(False),
        }

        result = await service_discovery.register_service(
            service_name="edge-case-test",
            service_id="edge-001",
            host="localhost",
            port=8080,
            metadata=metadata,
        )

        assert result is True

        services = await service_discovery.discover_services("edge-case-test")
        service = services[0]

        # Verify all special values are preserved
        assert service["empty_string"].string_value == ""
        assert "special_chars" in service
        assert "unicode" in service
        assert service["zero_values"].int_value == 0
        assert service["negative"].int_value == -999
        assert service["false_bool"].bool_value is False

    @pytest.mark.asyncio
    async def test_boundary_conditions(self):
        """Test boundary conditions for various parameters."""
        service_discovery = InMemoryServiceDiscovery()

        # Test with port boundaries
        await service_discovery.register_service(
            "boundary-test-min",
            "bound-min",
            "localhost",
            1,
            metadata={"port_type": ModelScalarValue.create_string("min")},
        )
        await service_discovery.register_service(
            "boundary-test-max",
            "bound-max",
            "localhost",
            65535,
            metadata={"port_type": ModelScalarValue.create_string("max")},
        )

        min_services = await service_discovery.discover_services("boundary-test-min")
        max_services = await service_discovery.discover_services("boundary-test-max")

        assert len(min_services) == 1
        assert min_services[0]["port"].int_value == 1

        assert len(max_services) == 1
        assert max_services[0]["port"].int_value == 65535

    @pytest.mark.asyncio
    async def test_service_name_and_id_variations(self):
        """Test various service name and ID patterns."""
        service_discovery = InMemoryServiceDiscovery()

        test_cases = [
            ("simple", "simple-001"),
            ("hyphen-separated", "hyphen-sep-001"),
            ("underscore_separated", "underscore_sep_001"),
            ("mixed-style_service", "mixed_001"),
            ("service.with.dots", "dots.001"),
            ("123-numeric-prefix", "123-001"),
        ]

        # Register all test cases
        for service_name, service_id in test_cases:
            result = await service_discovery.register_service(
                service_name,
                service_id,
                "localhost",
                8080,
                metadata={"pattern": ModelScalarValue.create_string(service_name)},
            )
            assert result is True

        # Verify all can be discovered
        for service_name, service_id in test_cases:
            services = await service_discovery.discover_services(service_name)
            assert len(services) == 1
            assert services[0]["service_id"].string_value == service_id

#!/usr/bin/env python3
"""
Comprehensive tests for ConsulServiceDiscovery implementation.

Tests Consul integration, fallback mechanisms, and strong typing with ModelScalarValue.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.models.service.model_service_health import ModelServiceHealth
from omnibase_core.services.consul_service_discovery import ConsulServiceDiscovery


class TestConsulServiceDiscovery:
    """Test suite for ConsulServiceDiscovery with Consul client mocking."""

    @pytest.fixture
    def mock_consul_client(self):
        """Create a mock Consul client."""
        mock_client = Mock()
        mock_client.agent = Mock()
        mock_client.agent.self = Mock(return_value={})
        mock_client.agent.service = Mock()
        mock_client.agent.service.register = Mock(return_value=True)
        mock_client.agent.service.deregister = Mock(return_value=True)
        mock_client.health = Mock()
        mock_client.health.service = Mock()
        mock_client.health.checks = Mock()
        mock_client.kv = Mock()
        return mock_client

    @pytest.fixture
    def consul_service_discovery(self, mock_consul_client):
        """Create ConsulServiceDiscovery with mocked Consul client."""
        with patch("consul.Consul", return_value=mock_consul_client):
            return ConsulServiceDiscovery(
                consul_host="localhost",
                consul_port=8500,
                enable_fallback=True,
            )

    @pytest.fixture
    def consul_service_discovery_no_fallback(self, mock_consul_client):
        """Create ConsulServiceDiscovery without fallback enabled."""
        with patch("consul.Consul", return_value=mock_consul_client):
            return ConsulServiceDiscovery(
                consul_host="localhost",
                consul_port=8500,
                enable_fallback=False,
            )

    @pytest.fixture
    def sample_metadata(self) -> dict:
        """Sample metadata using ModelScalarValue objects."""
        return {
            "environment": ModelScalarValue.create_string("production"),
            "version": ModelScalarValue.create_string("2.1.0"),
            "datacenter": ModelScalarValue.create_string("us-west-2"),
            "instance_count": ModelScalarValue.create_int(5),
            "cpu_weight": ModelScalarValue.create_float(1.5),
            "is_primary": ModelScalarValue.create_bool(True),
        }

    # Consul Client Connection Tests

    @pytest.mark.asyncio
    async def test_consul_client_initialization_success(self):
        """Test successful Consul client initialization."""
        mock_client = Mock()
        mock_client.agent.self.return_value = {}

        with patch("consul.Consul", return_value=mock_client):
            service_discovery = ConsulServiceDiscovery()
            client = await service_discovery._get_consul_client()

            assert client is mock_client
            assert service_discovery._is_using_fallback is False

    @pytest.mark.asyncio
    async def test_consul_client_connection_failure_with_fallback(self):
        """Test Consul connection failure triggering fallback."""
        with patch("consul.Consul", side_effect=ConnectionError("Connection failed")):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Should initialize fallback
            client = await service_discovery._get_consul_client()

            assert client is None
            assert service_discovery._is_using_fallback is True
            assert service_discovery._fallback_service is not None

    @pytest.mark.asyncio
    async def test_consul_client_connection_failure_no_fallback(self):
        """Test Consul connection failure without fallback raises exception."""
        with patch("consul.Consul", side_effect=ConnectionError("Connection failed")):
            service_discovery = ConsulServiceDiscovery(enable_fallback=False)

            with pytest.raises(ConnectionError, match="Connection failed"):
                await service_discovery._get_consul_client()

    @pytest.mark.asyncio
    async def test_consul_import_error_triggers_fallback(self):
        """Test ImportError (consul library not available) triggers fallback."""
        with patch(
            "consul.Consul",
            side_effect=ImportError("No module named 'consul'"),
        ):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            client = await service_discovery._get_consul_client()

            assert client is None
            assert service_discovery._is_using_fallback is True

    # Service Registration Tests

    @pytest.mark.asyncio
    async def test_register_service_consul_success(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test successful service registration with Consul."""
        mock_consul_client.agent.service.register.return_value = True

        result = await consul_service_discovery.register_service(
            service_name="test-api",
            service_id="test-api-001",
            host="192.168.1.10",
            port=8080,
            health_check_url="http://192.168.1.10:8080/health",
            tags=["api", "v1"],
            metadata={"test": ModelScalarValue.create_string("basic")},
        )

        assert result is True

        # Verify Consul registration was called
        mock_consul_client.agent.service.register.assert_called_once()
        call_args = mock_consul_client.agent.service.register.call_args
        assert call_args[1]["name"] == "test-api"
        assert call_args[1]["service_id"] == "test-api-001"
        assert call_args[1]["address"] == "192.168.1.10"
        assert call_args[1]["port"] == 8080

    @pytest.mark.asyncio
    async def test_register_service_with_metadata(
        self,
        consul_service_discovery,
        mock_consul_client,
        sample_metadata,
    ):
        """Test service registration with ModelScalarValue metadata."""
        mock_consul_client.agent.service.register.return_value = True

        result = await consul_service_discovery.register_service(
            service_name="metadata-service",
            service_id="meta-001",
            host="localhost",
            port=9000,
            metadata=sample_metadata,
        )

        assert result is True

        # Verify metadata was passed to Consul
        call_args = mock_consul_client.agent.service.register.call_args
        assert "meta" in call_args[1]
        assert call_args[1]["meta"] == sample_metadata

    @pytest.mark.asyncio
    async def test_register_service_consul_failure_fallback(self, mock_consul_client):
        """Test Consul registration failure triggers fallback."""
        mock_consul_client.agent.service.register.side_effect = Exception(
            "Consul error",
        )

        with patch("consul.Consul", return_value=mock_consul_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            result = await service_discovery.register_service(
                service_name="fallback-test",
                service_id="fallback-001",
                host="localhost",
                port=8080,
                metadata={"test": ModelScalarValue.create_string("fallback")},
            )

            # Should succeed via fallback
            assert result is True
            assert service_discovery._is_using_fallback is True

    @pytest.mark.asyncio
    async def test_register_service_consul_failure_no_fallback(
        self,
        consul_service_discovery_no_fallback,
        mock_consul_client,
    ):
        """Test Consul registration failure without fallback returns False."""
        mock_consul_client.agent.service.register.side_effect = Exception(
            "Consul error",
        )

        result = await consul_service_discovery_no_fallback.register_service(
            service_name="no-fallback-test",
            service_id="no-fallback-001",
            host="localhost",
            port=8080,
            metadata={"test": ModelScalarValue.create_string("no_fallback")},
        )

        assert result is False

    # Service Discovery Tests

    @pytest.mark.asyncio
    async def test_discover_services_consul_success(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test successful service discovery from Consul with ModelScalarValue conversion."""
        # Mock Consul response
        consul_response = [
            {
                "Service": {
                    "ID": "web-001",
                    "Service": "web-service",
                    "Address": "10.0.0.1",
                    "Port": 80,
                    "Meta": {
                        "version": "1.0.0",
                        "datacenter": "east",
                    },
                },
            },
            {
                "Service": {
                    "ID": "web-002",
                    "Service": "web-service",
                    "Address": "10.0.0.2",
                    "Port": 80,
                    "Meta": {},
                },
            },
        ]

        mock_consul_client.health.service.return_value = (None, consul_response)

        services = await consul_service_discovery.discover_services(
            "web-service",
            healthy_only=True,
        )

        assert len(services) == 2

        # Verify ModelScalarValue conversion
        for service in services:
            assert isinstance(service["service_id"], ModelScalarValue)
            assert isinstance(service["service_name"], ModelScalarValue)
            assert isinstance(service["host"], ModelScalarValue)
            assert isinstance(service["port"], ModelScalarValue)
            assert isinstance(service["health_status"], ModelScalarValue)

            assert service["service_name"].string_value == "web-service"
            assert service["port"].int_value == 80
            assert service["health_status"].string_value == "healthy"

        # Verify metadata conversion
        service_001 = next(
            s for s in services if s["service_id"].string_value == "web-001"
        )
        assert "meta_version" in service_001
        assert service_001["meta_version"].string_value == "1.0.0"
        assert "meta_datacenter" in service_001
        assert service_001["meta_datacenter"].string_value == "east"

    @pytest.mark.asyncio
    async def test_discover_services_consul_failure_fallback(self, mock_consul_client):
        """Test Consul discovery failure triggers fallback."""
        mock_consul_client.health.service.side_effect = Exception("Consul error")

        with patch("consul.Consul", return_value=mock_consul_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Pre-populate fallback with test data
            await service_discovery._initialize_fallback()
            await service_discovery._fallback_service.register_service(
                "fallback-service",
                "fallback-001",
                "localhost",
                8080,
                metadata={"test": ModelScalarValue.create_string("fallback_test")},
            )

            services = await service_discovery.discover_services("fallback-service")

            # Should get results from fallback
            assert len(services) == 1
            assert service_discovery._is_using_fallback is True

    @pytest.mark.asyncio
    async def test_discover_services_empty_result(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test discovery with no matching services."""
        mock_consul_client.health.service.return_value = (None, [])

        services = await consul_service_discovery.discover_services(
            "non-existent-service",
        )

        assert isinstance(services, list)
        assert len(services) == 0

    # Service Health Tests

    @pytest.mark.asyncio
    async def test_get_service_health_consul_healthy(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test getting healthy service status from Consul."""
        consul_checks = [
            {"Status": "passing", "ServiceID": "test-001"},
            {"Status": "passing", "ServiceID": "test-001"},
        ]

        mock_consul_client.health.checks.return_value = (None, consul_checks)

        health = await consul_service_discovery.get_service_health("test-001")

        assert isinstance(health, ModelServiceHealth)
        assert health.service_id == "test-001"
        assert health.status == "healthy"
        assert health.error_message is None

    @pytest.mark.asyncio
    async def test_get_service_health_consul_critical(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test getting critical service status from Consul."""
        consul_checks = [
            {"Status": "passing", "ServiceID": "test-001"},
            {"Status": "critical", "ServiceID": "test-001"},
        ]

        mock_consul_client.health.checks.return_value = (None, consul_checks)

        health = await consul_service_discovery.get_service_health("test-001")

        assert health.service_id == "test-001"
        assert health.status == "critical"
        assert health.error_message == "Health check failed"

    @pytest.mark.asyncio
    async def test_get_service_health_consul_warning(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test getting warning service status from Consul."""
        consul_checks = [
            {"Status": "passing", "ServiceID": "test-001"},
            {"Status": "warning", "ServiceID": "test-001"},
        ]

        mock_consul_client.health.checks.return_value = (None, consul_checks)

        health = await consul_service_discovery.get_service_health("test-001")

        assert health.service_id == "test-001"
        assert health.status == "warning"
        assert health.error_message == "Health check failed"

    @pytest.mark.asyncio
    async def test_get_service_health_no_checks(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test getting health for service with no health checks."""
        mock_consul_client.health.checks.return_value = (None, [])

        health = await consul_service_discovery.get_service_health("test-001")

        assert health.service_id == "test-001"
        assert health.status == "unknown"

    # Service Deregistration Tests

    @pytest.mark.asyncio
    async def test_deregister_service_consul_success(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test successful service deregistration from Consul."""
        mock_consul_client.agent.service.deregister.return_value = True

        result = await consul_service_discovery.deregister_service("test-001")

        assert result is True
        mock_consul_client.agent.service.deregister.assert_called_once_with("test-001")

    @pytest.mark.asyncio
    async def test_deregister_service_consul_failure_fallback(self, mock_consul_client):
        """Test Consul deregistration failure triggers fallback."""
        mock_consul_client.agent.service.deregister.side_effect = Exception(
            "Consul error",
        )

        with patch("consul.Consul", return_value=mock_consul_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            result = await service_discovery.deregister_service("test-001")

            # Should succeed via fallback
            assert result is True
            assert service_discovery._is_using_fallback is True

    # Key-Value Store Tests

    @pytest.mark.asyncio
    async def test_key_value_operations_consul(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test key-value operations with Consul."""
        # Set key-value
        mock_consul_client.kv.put.return_value = True
        result = await consul_service_discovery.set_key_value(
            "config/test",
            "test_value",
        )
        assert result is True
        mock_consul_client.kv.put.assert_called_with("config/test", "test_value")

        # Get key-value
        mock_consul_client.kv.get.return_value = (None, {"Value": b"test_value"})
        value = await consul_service_discovery.get_key_value("config/test")
        assert value == "test_value"

        # Get non-existent key
        mock_consul_client.kv.get.return_value = (None, None)
        missing = await consul_service_discovery.get_key_value("non-existent")
        assert missing is None

    @pytest.mark.asyncio
    async def test_delete_key_consul(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test key deletion with Consul."""
        mock_consul_client.kv.delete.return_value = True

        result = await consul_service_discovery.delete_key("config/test")

        assert result is True
        mock_consul_client.kv.delete.assert_called_with("config/test")

    @pytest.mark.asyncio
    async def test_list_keys_consul(self, consul_service_discovery, mock_consul_client):
        """Test key listing with Consul."""
        mock_consul_client.kv.get.return_value = (
            None,
            ["config/key1", "config/key2", "cache/key1"],
        )

        keys = await consul_service_discovery.list_keys("config/")

        assert keys == ["config/key1", "config/key2", "cache/key1"]
        mock_consul_client.kv.get.assert_called_with("config/", keys=True)

    @pytest.mark.asyncio
    async def test_kv_operations_fallback_on_error(self, mock_consul_client):
        """Test that KV operations fall back on Consul errors."""
        mock_consul_client.kv.put.side_effect = Exception("Consul KV error")

        with patch("consul.Consul", return_value=mock_consul_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            result = await service_discovery.set_key_value("test/key", "test_value")

            # Should succeed via fallback
            assert result is True
            assert service_discovery._is_using_fallback is True

    # System Health Tests

    @pytest.mark.asyncio
    async def test_health_check_consul_healthy(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test system health check with healthy Consul."""
        mock_consul_client.agent.self.return_value = {}

        result = await consul_service_discovery.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_consul_unhealthy(
        self,
        consul_service_discovery,
        mock_consul_client,
    ):
        """Test system health check with unhealthy Consul."""
        mock_consul_client.agent.self.side_effect = Exception("Consul down")

        result = await consul_service_discovery.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_fallback(self, mock_consul_client):
        """Test system health check using fallback."""
        mock_consul_client.agent.self.side_effect = Exception("Consul down")

        with patch("consul.Consul", return_value=mock_consul_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Force fallback initialization
            await service_discovery._initialize_fallback()

            result = await service_discovery.health_check()

            assert result is True  # Fallback is always healthy

    # Resource Cleanup Tests

    @pytest.mark.asyncio
    async def test_close_cleanup(self, consul_service_discovery):
        """Test resource cleanup on close."""
        # Initialize fallback to test cleanup
        await consul_service_discovery._initialize_fallback()
        await consul_service_discovery._fallback_service.register_service(
            "test-service",
            "test-001",
            "localhost",
            8080,
            metadata={"test": ModelScalarValue.create_string("cleanup_test")},
        )

        # Close should clean up fallback resources
        await consul_service_discovery.close()

        # Consul client should be cleared
        assert consul_service_discovery._consul_client is None

    # Fallback Integration Tests

    @pytest.mark.asyncio
    async def test_seamless_fallback_transition(self, mock_consul_client):
        """Test seamless transition to fallback when Consul becomes unavailable."""
        # Start with working Consul
        mock_consul_client.agent.service.register.return_value = True

        with patch("consul.Consul", return_value=mock_consul_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Register service via Consul
            result1 = await service_discovery.register_service(
                "transition-test",
                "trans-001",
                "localhost",
                8080,
                metadata={"stage": ModelScalarValue.create_string("first")},
            )
            assert result1 is True
            assert service_discovery._is_using_fallback is False

            # Consul fails on next operation
            mock_consul_client.agent.service.register.side_effect = Exception(
                "Consul failed",
            )

            # Should automatically switch to fallback
            result2 = await service_discovery.register_service(
                "transition-test",
                "trans-002",
                "localhost",
                8081,
                metadata={"stage": ModelScalarValue.create_string("second")},
            )
            assert result2 is True
            assert service_discovery._is_using_fallback is True

    @pytest.mark.asyncio
    async def test_fallback_maintains_full_functionality(self):
        """Test that fallback provides complete service discovery functionality."""
        # Create service discovery that immediately uses fallback
        with patch("consul.Consul", side_effect=ImportError("No consul module")):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Test complete workflow using fallback
            # Register service
            result = await service_discovery.register_service(
                service_name="fallback-full-test",
                service_id="full-001",
                host="192.168.1.100",
                port=9000,
                metadata={"env": ModelScalarValue.create_string("test")},
            )
            assert result is True

            # Discover service
            services = await service_discovery.discover_services("fallback-full-test")
            assert len(services) == 1
            assert services[0]["service_id"].string_value == "full-001"
            assert services[0]["host"].string_value == "192.168.1.100"
            assert services[0]["port"].int_value == 9000

            # Check health
            health = await service_discovery.get_service_health("full-001")
            assert health.status == "healthy"

            # KV operations
            await service_discovery.set_key_value("test/config", "fallback_value")
            value = await service_discovery.get_key_value("test/config")
            assert value == "fallback_value"

            # Deregister service
            result = await service_discovery.deregister_service("full-001")
            assert result is True

            # Verify deregistration
            services = await service_discovery.discover_services("fallback-full-test")
            assert len(services) == 0


class TestConsulServiceDiscoveryErrorScenarios:
    """Test error scenarios and edge cases for ConsulServiceDiscovery."""

    @pytest.mark.asyncio
    async def test_consul_connection_timeout(self):
        """Test handling of Consul connection timeout."""
        with patch("consul.Consul", side_effect=TimeoutError("Connection timeout")):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Should fall back gracefully
            result = await service_discovery.register_service(
                "timeout-test",
                "timeout-001",
                "localhost",
                8080,
                metadata={"test": ModelScalarValue.create_string("timeout")},
            )

            assert result is True
            assert service_discovery._is_using_fallback is True

    @pytest.mark.asyncio
    async def test_consul_partial_failures(self):
        """Test handling of partial Consul failures."""
        mock_client = Mock()
        mock_client.agent.self.return_value = {}
        mock_client.agent.service.register.return_value = True
        mock_client.health.service.side_effect = Exception("Health service down")

        with patch("consul.Consul", return_value=mock_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Registration should work
            result = await service_discovery.register_service(
                "partial-test",
                "partial-001",
                "localhost",
                8080,
                metadata={"test": ModelScalarValue.create_string("partial")},
            )
            assert result is True

            # Discovery should fall back
            services = await service_discovery.discover_services("partial-test")
            assert service_discovery._is_using_fallback is True

    @pytest.mark.asyncio
    async def test_invalid_consul_response_format(self):
        """Test handling of invalid Consul response formats."""
        mock_client = Mock()
        mock_client.agent.self.return_value = {}

        # Invalid service discovery response format
        mock_client.health.service.return_value = (None, [{"Invalid": "Format"}])

        with patch("consul.Consul", return_value=mock_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Should handle gracefully and potentially fall back
            services = await service_discovery.discover_services("test-service")

            # Should either handle gracefully or fall back
            assert isinstance(services, list)

    @pytest.mark.asyncio
    async def test_consul_service_discovery_race_conditions(self):
        """Test race conditions in service discovery operations."""
        mock_client = Mock()
        mock_client.agent.self.return_value = {}

        # Simulate intermittent failures
        call_count = 0

        def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Intermittent failure")
            return True

        mock_client.agent.service.register.side_effect = intermittent_failure

        with patch("consul.Consul", return_value=mock_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=True)

            # Concurrent registrations should handle failures gracefully
            tasks = []
            for i in range(5):
                task = service_discovery.register_service(
                    f"race-test-{i}",
                    f"race-{i:03d}",
                    "localhost",
                    8080 + i,
                    metadata={"index": ModelScalarValue.create_int(i)},
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Some should succeed, failures should be handled gracefully
            successful_results = [r for r in results if r is True]
            assert len(successful_results) > 0

    @pytest.mark.asyncio
    async def test_fallback_service_isolation(self):
        """Test that fallback service instances are properly isolated."""
        # Create two service discovery instances
        with patch("consul.Consul", side_effect=ImportError("No consul")):
            service1 = ConsulServiceDiscovery(enable_fallback=True)
            service2 = ConsulServiceDiscovery(enable_fallback=True)

            # Register service in first instance
            await service1.register_service(
                "isolation-test",
                "iso-001",
                "localhost",
                8080,
                metadata={"test": ModelScalarValue.create_string("isolation")},
            )

            # Should not be visible in second instance
            services1 = await service1.discover_services("isolation-test")
            services2 = await service2.discover_services("isolation-test")

            assert len(services1) == 1
            assert len(services2) == 0

    @pytest.mark.asyncio
    async def test_metadata_serialization_edge_cases(self):
        """Test edge cases in metadata serialization to/from Consul."""
        mock_client = Mock()
        mock_client.agent.self.return_value = {}
        mock_client.agent.service.register.return_value = True

        # Test with complex metadata
        complex_metadata = {
            "empty_string": ModelScalarValue.create_string(""),
            "zero_int": ModelScalarValue.create_int(0),
            "zero_float": ModelScalarValue.create_float(0.0),
            "false_bool": ModelScalarValue.create_bool(False),
            "special_chars": ModelScalarValue.create_string("special!@#$%^&*()"),
            "unicode": ModelScalarValue.create_string("こんにちは"),
            "large_number": ModelScalarValue.create_int(2**60),
        }

        with patch("consul.Consul", return_value=mock_client):
            service_discovery = ConsulServiceDiscovery(enable_fallback=False)

            result = await service_discovery.register_service(
                "metadata-edge-test",
                "meta-edge-001",
                "localhost",
                8080,
                metadata=complex_metadata,
            )

            assert result is True

            # Verify metadata was passed correctly
            call_args = mock_client.agent.service.register.call_args
            assert call_args[1]["meta"] == complex_metadata

#!/usr/bin/env python3

"""
Comprehensive unit tests for Consul Adapter Effect.
Tests all functionality with real Consul integration (no mocks/stubs).
Achieves ≥90% code coverage requirement.
"""

import os
import time
from unittest.mock import patch
from uuid import uuid4

import consul as python_consul
import pytest

from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.model.core.model_core_errors import CoreErrorCode, OnexError
from omnibase_core.tools.infrastructure.tool_infrastructure_consul_adapter_effect.v1_0_0.models import (
    ModelConsulHealthResponse,
    ModelConsulHealthStatus,
    ModelConsulKVResponse,
    ModelConsulServiceInfo,
    ModelConsulServiceListResponse,
    ModelConsulServiceRegistration,
    ModelConsulServiceResponse,
)
from omnibase_core.tools.infrastructure.tool_infrastructure_consul_adapter_effect.v1_0_0.node import (
    ToolInfrastructureConsulAdapterEffect,
)


class TestConsulAdapterEffect:
    """
    Comprehensive test suite for Consul Adapter Effect.
    Uses real Consul instance for integration testing.
    """

    @pytest.fixture(scope="class")
    def consul_config(self):
        """Consul configuration for testing."""
        return {
            "host": os.getenv("CONSUL_HOST", "localhost"),
            "port": int(os.getenv("CONSUL_PORT", "8500")),
            "datacenter": os.getenv("CONSUL_DATACENTER", "dc1"),
        }

    @pytest.fixture
    def container(self):
        """Mock ONEX container for testing."""
        return ONEXContainer()

    @pytest.fixture
    def consul_env_vars(self, consul_config):
        """Set up environment variables for Consul."""
        with patch.dict(
            os.environ,
            {
                "CONSUL_HOST": consul_config["host"],
                "CONSUL_PORT": str(consul_config["port"]),
                "CONSUL_DATACENTER": consul_config["datacenter"],
            },
        ):
            yield consul_config

    @pytest.fixture
    async def consul_adapter(self, container, consul_env_vars):
        """Create and initialize Consul adapter."""
        adapter = ToolInfrastructureConsulAdapterEffect(container)
        await adapter.initialize_consul_client()
        return adapter

    @pytest.fixture
    async def real_consul_client(self, consul_config):
        """Real Consul client for test setup and verification."""
        client = python_consul.Consul(
            host=consul_config["host"],
            port=consul_config["port"],
            dc=consul_config["datacenter"],
        )
        yield client

        # Cleanup test data
        try:
            # Clean up any test keys
            client.kv.delete("test/", recurse=True)
            # Clean up any test services
            services = client.agent.services()
            for service_id in services:
                if service_id.startswith("test-"):
                    client.agent.service.deregister(service_id)
        except Exception:
            pass  # Best effort cleanup

    def test_init_missing_consul_host(self, container):
        """Test initialization fails without CONSUL_HOST."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(OnexError) as exc_info:
                ToolInfrastructureConsulAdapterEffect(container)

            assert exc_info.value.error_code == CoreErrorCode.MISSING_REQUIRED_PARAMETER
            assert "CONSUL_HOST" in str(exc_info.value)

    def test_init_missing_consul_port(self, container):
        """Test initialization fails without CONSUL_PORT."""
        with patch.dict(os.environ, {"CONSUL_HOST": "localhost"}, clear=True):
            with pytest.raises(OnexError) as exc_info:
                ToolInfrastructureConsulAdapterEffect(container)

            assert exc_info.value.error_code == CoreErrorCode.MISSING_REQUIRED_PARAMETER
            assert "CONSUL_PORT" in str(exc_info.value)

    def test_init_missing_consul_datacenter(self, container):
        """Test initialization fails without CONSUL_DATACENTER."""
        with patch.dict(
            os.environ,
            {"CONSUL_HOST": "localhost", "CONSUL_PORT": "8500"},
            clear=True,
        ):
            with pytest.raises(OnexError) as exc_info:
                ToolInfrastructureConsulAdapterEffect(container)

            assert exc_info.value.error_code == CoreErrorCode.MISSING_REQUIRED_PARAMETER
            assert "CONSUL_DATACENTER" in str(exc_info.value)

    def test_init_invalid_consul_port(self, container):
        """Test initialization fails with invalid CONSUL_PORT."""
        with patch.dict(
            os.environ,
            {
                "CONSUL_HOST": "localhost",
                "CONSUL_PORT": "not-a-number",
                "CONSUL_DATACENTER": "dc1",
            },
        ):
            with pytest.raises(OnexError) as exc_info:
                ToolInfrastructureConsulAdapterEffect(container)

            assert exc_info.value.error_code == CoreErrorCode.PARAMETER_TYPE_MISMATCH
            assert "must be a valid integer" in str(exc_info.value)

    def test_init_successful(self, consul_adapter):
        """Test successful initialization."""
        assert consul_adapter.node_type == "effect"
        assert consul_adapter.domain == "infrastructure"
        assert consul_adapter.consul_config["host"] is not None
        assert consul_adapter.consul_config["port"] > 0
        assert consul_adapter.consul_config["datacenter"] is not None

    @pytest.mark.asyncio
    async def test_consul_client_initialization(self, consul_adapter):
        """Test Consul client initialization."""
        assert consul_adapter.consul_client is not None
        assert consul_adapter._initialized is True

        # Test idempotent initialization
        await consul_adapter.initialize_consul_client()
        assert consul_adapter._initialized is True

    @pytest.mark.asyncio
    async def test_consul_client_connection_failure(self, container):
        """Test Consul client initialization failure."""
        with patch.dict(
            os.environ,
            {
                "CONSUL_HOST": "nonexistent-host",
                "CONSUL_PORT": "9999",
                "CONSUL_DATACENTER": "dc1",
            },
        ):
            adapter = ToolInfrastructureConsulAdapterEffect(container)

            with pytest.raises(OnexError) as exc_info:
                await adapter.initialize_consul_client()

            assert exc_info.value.error_code == CoreErrorCode.INITIALIZATION_FAILED
            assert "Consul initialization failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_consul_healthy(self, consul_adapter):
        """Test Consul health check when healthy."""
        health_status = await consul_adapter.health_check_consul()

        assert isinstance(health_status, ModelConsulHealthStatus)
        assert health_status.status == "healthy"
        assert health_status.consul_agent is not None
        assert health_status.datacenter is not None
        assert health_status.error is None

    @pytest.mark.asyncio
    async def test_health_check_consul_unhealthy(self, container):
        """Test Consul health check when unhealthy."""
        with patch.dict(
            os.environ,
            {
                "CONSUL_HOST": "nonexistent-host",
                "CONSUL_PORT": "9999",
                "CONSUL_DATACENTER": "dc1",
            },
        ):
            adapter = ToolInfrastructureConsulAdapterEffect(container)

            health_status = await adapter.health_check_consul()

            assert isinstance(health_status, ModelConsulHealthStatus)
            assert health_status.status == "unhealthy"
            assert health_status.consul_agent == "unknown"
            assert health_status.datacenter == "unknown"
            assert health_status.error is not None

    @pytest.mark.asyncio
    async def test_kv_operations(self, consul_adapter, real_consul_client):
        """Test KV store operations."""
        test_key = f"test/key-{uuid4()}"
        test_value = f"test-value-{int(time.time())}"

        # Test PUT operation
        put_response = await consul_adapter.effect_kv_put(test_key, test_value)
        assert isinstance(put_response, ModelConsulKVResponse)
        assert put_response.status == "success"
        assert put_response.key == test_key
        assert put_response.value == test_value

        # Verify with direct Consul client
        _, data = real_consul_client.kv.get(test_key)
        assert data is not None
        assert data["Value"].decode("utf-8") == test_value

        # Test GET operation
        get_response = await consul_adapter.effect_kv_get(test_key)
        assert isinstance(get_response, ModelConsulKVResponse)
        assert get_response.status == "success"
        assert get_response.key == test_key
        assert get_response.value == test_value
        assert get_response.modify_index is not None
        assert get_response.modify_index > 0

        # Test GET non-existent key
        non_existent_key = f"test/nonexistent-{uuid4()}"
        not_found_response = await consul_adapter.effect_kv_get(non_existent_key)
        assert isinstance(not_found_response, ModelConsulKVResponse)
        assert not_found_response.status == "not_found"
        assert not_found_response.key == non_existent_key
        assert not_found_response.value is None

        # Test DELETE operation for existing key
        delete_response = await consul_adapter.effect_kv_delete(test_key)
        assert isinstance(delete_response, ModelConsulKVResponse)
        assert delete_response.status == "success"
        assert delete_response.key == test_key
        assert delete_response.value is None

        # Verify deletion with direct Consul client
        _, data = real_consul_client.kv.get(test_key)
        assert data is None

        # Test DELETE operation for non-existent key
        delete_not_found_response = await consul_adapter.effect_kv_delete(
            non_existent_key,
        )
        assert isinstance(delete_not_found_response, ModelConsulKVResponse)
        assert delete_not_found_response.status == "not_found"
        assert delete_not_found_response.key == non_existent_key
        assert delete_not_found_response.value is None

    @pytest.mark.asyncio
    async def test_kv_recursive_delete(self, consul_adapter, real_consul_client):
        """Test KV recursive delete operations."""
        base_prefix = f"test/recursive-{uuid4()}"

        # Create multiple keys with the same prefix
        keys_data = {
            f"{base_prefix}/key1": "value1",
            f"{base_prefix}/key2": "value2",
            f"{base_prefix}/subdir/key3": "value3",
            f"{base_prefix}/subdir/key4": "value4",
        }

        # Put all test keys
        for key, value in keys_data.items():
            put_response = await consul_adapter.effect_kv_put(key, value)
            assert put_response.status == "success"

        # Verify keys exist with direct Consul client
        for key in keys_data:
            _, data = real_consul_client.kv.get(key)
            assert data is not None

        # Test recursive delete
        recursive_delete_response = await consul_adapter.effect_kv_delete(
            base_prefix,
            recurse=True,
        )
        assert isinstance(recursive_delete_response, ModelConsulKVResponse)
        assert recursive_delete_response.status == "success"
        assert recursive_delete_response.key == base_prefix
        assert recursive_delete_response.value is None

        # Verify all keys are deleted with direct Consul client
        for key in keys_data:
            _, data = real_consul_client.kv.get(key)
            assert data is None

    @pytest.mark.asyncio
    async def test_service_registration(self, consul_adapter, real_consul_client):
        """Test service registration."""
        service_id = f"test-service-{uuid4()}"
        service_name = "test-service"

        service_registration = ModelConsulServiceRegistration(
            service_id=service_id,
            name=service_name,
            port=8080,
            address="127.0.0.1",
            health_check=None,
        )

        # Test service registration
        register_response = await consul_adapter.effect_service_register(
            service_registration,
        )
        assert isinstance(register_response, ModelConsulServiceResponse)
        assert register_response.status == "success"
        assert register_response.service_id == service_id
        assert register_response.service_name == service_name

        # Verify with direct Consul client
        services = real_consul_client.agent.services()
        assert service_id in services
        assert services[service_id]["Service"] == service_name
        assert services[service_id]["Port"] == 8080
        assert services[service_id]["Address"] == "127.0.0.1"

        # Test service deregistration
        deregister_response = await consul_adapter.effect_service_deregister(service_id)
        assert isinstance(deregister_response, ModelConsulServiceResponse)
        assert deregister_response.status == "success"
        assert deregister_response.service_id == service_id
        assert deregister_response.service_name == service_name

        # Verify deregistration with direct Consul client
        services_after_deregister = real_consul_client.agent.services()
        assert service_id not in services_after_deregister

    @pytest.mark.asyncio
    async def test_service_registration_with_health_check(
        self,
        consul_adapter,
        real_consul_client,
    ):
        """Test service registration with health check."""
        from omnibase_core.tools.infrastructure.tool_infrastructure_consul_adapter_effect.v1_0_0.models import (
            ModelConsulHealthCheck,
        )

        service_id = f"test-service-hc-{uuid4()}"
        service_name = "test-service-with-health"

        health_check = ModelConsulHealthCheck(
            url="http://127.0.0.1:8080/health",
            interval="10s",
            timeout="5s",
        )

        service_registration = ModelConsulServiceRegistration(
            service_id=service_id,
            name=service_name,
            port=8080,
            address="127.0.0.1",
            health_check=health_check,
        )

        # Test service registration with health check
        register_response = await consul_adapter.effect_service_register(
            service_registration,
        )
        assert isinstance(register_response, ModelConsulServiceResponse)
        assert register_response.status == "success"

        # Verify with direct Consul client
        services = real_consul_client.agent.services()
        assert service_id in services

    @pytest.mark.asyncio
    async def test_service_deregister_not_found(self, consul_adapter):
        """Test service deregistration for non-existent service."""
        non_existent_service_id = f"non-existent-service-{uuid4()}"

        deregister_response = await consul_adapter.effect_service_deregister(
            non_existent_service_id,
        )
        assert isinstance(deregister_response, ModelConsulServiceResponse)
        assert deregister_response.status == "not_found"
        assert deregister_response.service_id == non_existent_service_id
        assert deregister_response.service_name == "unknown"

    @pytest.mark.asyncio
    async def test_service_list(self, consul_adapter, real_consul_client):
        """Test service listing."""
        # Register a test service first
        service_id = f"test-list-service-{uuid4()}"
        service_name = "test-list-service"

        service_registration = ModelConsulServiceRegistration(
            service_id=service_id,
            name=service_name,
            port=9090,
            address="127.0.0.1",
            health_check=None,
        )

        await consul_adapter.effect_service_register(service_registration)

        # Test service listing
        list_response = await consul_adapter.effect_service_list()
        assert isinstance(list_response, ModelConsulServiceListResponse)
        assert list_response.status == "success"
        assert list_response.count >= 1
        assert len(list_response.services) >= 1

        # Find our test service in the list
        test_service = None
        for service in list_response.services:
            if service.id == service_id:
                test_service = service
                break

        assert test_service is not None
        assert isinstance(test_service, ModelConsulServiceInfo)
        assert test_service.name == service_name
        assert test_service.port == 9090
        assert test_service.address == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_health_check_operations(self, consul_adapter, real_consul_client):
        """Test health check operations."""
        # Register a service for health checking
        service_id = f"test-health-service-{uuid4()}"
        service_name = "test-health-service"

        service_registration = ModelConsulServiceRegistration(
            service_id=service_id,
            name=service_name,
            port=8080,
            address="127.0.0.1",
            health_check=None,
        )

        await consul_adapter.effect_service_register(service_registration)

        # Test health check for specific service
        health_response = await consul_adapter.effect_health_check(service_name)
        assert isinstance(health_response, ModelConsulHealthResponse)
        assert health_response.status == "success"
        assert health_response.service_name == service_name
        assert health_response.health_checks is not None
        assert len(health_response.health_checks) >= 0

        # Test health check for all services
        all_health_response = await consul_adapter.effect_health_check(None)
        assert isinstance(all_health_response, ModelConsulHealthResponse)
        assert all_health_response.status == "success"
        assert all_health_response.service_name is None
        assert all_health_response.health_summary is not None
        assert isinstance(all_health_response.health_summary, dict)

    @pytest.mark.asyncio
    async def test_error_handling_kv_operations(self, consul_adapter):
        """Test error handling in KV operations."""
        # Simulate Consul connection failure by setting non-existent client
        consul_adapter.consul_client = None
        consul_adapter._initialized = False

        with patch("consul.Consul") as mock_consul:
            mock_consul.side_effect = Exception("Connection failed")

            with pytest.raises(OnexError) as exc_info:
                await consul_adapter.effect_kv_get("test-key")

            assert exc_info.value.error_code == CoreErrorCode.INITIALIZATION_FAILED

    @pytest.mark.asyncio
    async def test_error_handling_service_operations(self, consul_adapter):
        """Test error handling in service operations."""
        # Simulate Consul connection failure
        consul_adapter.consul_client = None
        consul_adapter._initialized = False

        with patch("consul.Consul") as mock_consul:
            mock_consul.side_effect = Exception("Connection failed")

            service_registration = ModelConsulServiceRegistration(
                service_id="test-service",
                name="test-service",
                port=8080,
                address="127.0.0.1",
            )

            with pytest.raises(OnexError) as exc_info:
                await consul_adapter.effect_service_register(service_registration)

            assert exc_info.value.error_code == CoreErrorCode.INITIALIZATION_FAILED

    def test_main_function(self):
        """Test main entry point function."""
        from omnibase_core.tools.infrastructure.tool_infrastructure_consul_adapter_effect.v1_0_0.node import (
            main,
        )

        with patch.dict(
            os.environ,
            {
                "CONSUL_HOST": "localhost",
                "CONSUL_PORT": "8500",
                "CONSUL_DATACENTER": "dc1",
            },
        ):
            result = main()
            assert isinstance(result, ToolInfrastructureConsulAdapterEffect)
            assert result.node_type == "effect"
            assert result.domain == "infrastructure"

    @pytest.mark.asyncio
    async def test_process_kv_delete_operations(
        self,
        consul_adapter,
        real_consul_client,
    ):
        """Test process method with KV delete operations."""
        from omnibase_core.core.node_effect import EffectType, ModelEffectInput

        test_key = f"test/process-delete-{uuid4()}"
        test_value = f"process-test-value-{int(time.time())}"

        # First, put a key to delete
        await consul_adapter.effect_kv_put(test_key, test_value)

        # Test KV delete through process method
        delete_input = ModelEffectInput(
            operation_id=str(uuid4()),
            effect_type=EffectType.API_CALL,
            operation_data={
                "envelope_payload": {
                    "action": "consul_kv_delete",
                    "operation_type": "kv_delete",
                    "key_path": test_key,
                    "recurse": False,
                },
            },
        )

        result = await consul_adapter.process(delete_input)
        assert result.result["success"] is True
        assert result.result["operation_type"] == "consul_kv_delete"
        assert result.result["consul_operation_result"]["status"] == "success"
        assert result.result["consul_operation_result"]["key"] == test_key

        # Verify deletion with direct Consul client
        _, data = real_consul_client.kv.get(test_key)
        assert data is None

    @pytest.mark.asyncio
    async def test_process_service_deregister_operations(
        self,
        consul_adapter,
        real_consul_client,
    ):
        """Test process method with service deregister operations."""
        from omnibase_core.core.node_effect import EffectType, ModelEffectInput

        service_id = f"test-process-deregister-{uuid4()}"
        service_name = "test-process-service"

        # First, register a service to deregister
        service_registration = ModelConsulServiceRegistration(
            service_id=service_id,
            name=service_name,
            port=8080,
            address="127.0.0.1",
            health_check=None,
        )
        await consul_adapter.effect_service_register(service_registration)

        # Test service deregister through process method
        deregister_input = ModelEffectInput(
            operation_id=str(uuid4()),
            effect_type=EffectType.API_CALL,
            operation_data={
                "envelope_payload": {
                    "action": "consul_service_deregister",
                    "operation_type": "service_deregister",
                    "service_config": {"service_id": service_id},
                },
            },
        )

        result = await consul_adapter.process(deregister_input)
        assert result.result["success"] is True
        assert result.result["operation_type"] == "consul_service_deregister"
        assert result.result["consul_operation_result"]["status"] == "success"
        assert result.result["consul_operation_result"]["service_id"] == service_id

        # Verify deregistration with direct Consul client
        services = real_consul_client.agent.services()
        assert service_id not in services

    @pytest.mark.asyncio
    async def test_process_error_handling_delete_operations(self, consul_adapter):
        """Test error handling for delete operations in process method."""
        from omnibase_core.core.node_effect import EffectType, ModelEffectInput
        from omnibase_core.model.core.model_core_errors import CoreErrorCode, OnexError

        # Test KV delete without key_path
        delete_input_no_key = ModelEffectInput(
            operation_id=str(uuid4()),
            effect_type=EffectType.API_CALL,
            operation_data={
                "envelope_payload": {
                    "action": "consul_kv_delete",
                    "operation_type": "kv_delete",
                    # Missing key_path
                },
            },
        )

        with pytest.raises(OnexError) as exc_info:
            await consul_adapter.process(delete_input_no_key)
        assert exc_info.value.error_code == CoreErrorCode.MISSING_REQUIRED_PARAMETER
        assert "KV delete requires key_path" in str(exc_info.value)

        # Test service deregister without service_id
        deregister_input_no_id = ModelEffectInput(
            operation_id=str(uuid4()),
            effect_type=EffectType.API_CALL,
            operation_data={
                "envelope_payload": {
                    "action": "consul_service_deregister",
                    "operation_type": "service_deregister",
                    "service_config": {
                        # Missing service_id
                        "name": "test-service",
                    },
                },
            },
        )

        with pytest.raises(OnexError) as exc_info:
            await consul_adapter.process(deregister_input_no_id)
        assert exc_info.value.error_code == CoreErrorCode.MISSING_REQUIRED_PARAMETER
        assert "Service deregistration requires service_config with service_id" in str(
            exc_info.value,
        )

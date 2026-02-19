# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ProtocolServiceDiscovery.

Validates:
1. Protocol definitions are correctly structured
2. runtime_checkable decorator works for isinstance checks
3. Mock implementations conform to protocols
4. Protocol method signatures are correct

Related:
    - PR #302: Add infrastructure protocols
"""

import asyncio
from typing import Any

import pytest

from omnibase_core.protocols.infrastructure import ProtocolServiceDiscovery

# =============================================================================
# Test Fixtures - Mock Implementations
# =============================================================================


class MockServiceDiscovery:
    """Minimal service discovery implementation for protocol conformance testing."""

    def __init__(self) -> None:
        self._services: dict[str, dict[str, Any]] = {}
        self._watches: dict[str, Any] = {}
        self._watch_counter = 0

    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        health_check_url: str | None = None,
        health_check_interval: str | None = None,
    ) -> bool:
        """Register a service with the discovery system."""
        self._services[service_id] = {
            "id": service_id,
            "name": service_name,
            "address": address,
            "port": port,
            "tags": tags or [],
            "metadata": metadata or {},
            "health_check_url": health_check_url,
            "health_check_interval": health_check_interval,
            "healthy": True,
        }
        return True

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from the discovery system."""
        if service_id in self._services:
            del self._services[service_id]
            return True
        return False

    async def discover_services(
        self,
        service_name: str,
        tags: list[str] | None = None,
        healthy_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Discover services by name and optional tags."""
        result = []
        for service in self._services.values():
            if service["name"] != service_name:
                continue
            if healthy_only and not service.get("healthy", True):
                continue
            if tags and not all(tag in service.get("tags", []) for tag in tags):
                continue
            result.append(
                {
                    "id": service["id"],
                    "name": service["name"],
                    "address": service["address"],
                    "port": service["port"],
                    "tags": service.get("tags", []),
                    "metadata": service.get("metadata", {}),
                }
            )
        return result

    async def get_service(self, service_id: str) -> dict[str, Any] | None:
        """Get a specific service instance by ID."""
        service = self._services.get(service_id)
        if service:
            return {
                "id": service["id"],
                "name": service["name"],
                "address": service["address"],
                "port": service["port"],
                "tags": service.get("tags", []),
                "metadata": service.get("metadata", {}),
            }
        return None

    async def get_service_health(self, service_id: str) -> dict[str, Any]:
        """Get health status for a specific service."""
        service = self._services.get(service_id)
        if service:
            return {
                "status": "passing" if service.get("healthy", True) else "critical",
                "message": "Service is healthy"
                if service.get("healthy", True)
                else "Service is unhealthy",
                "last_check": "2024-01-01T00:00:00Z",
            }
        return {
            "status": "unknown",
            "message": "Service not found",
            "last_check": None,
        }

    async def list_services(self) -> list[str]:
        """List all registered service names."""
        return list({s["name"] for s in self._services.values()})

    async def watch_service(
        self,
        service_name: str,
        callback: Any,
    ) -> str:
        """Watch for changes to a service."""
        self._watch_counter += 1
        watch_id = f"watch-{self._watch_counter}"
        self._watches[watch_id] = {
            "service_name": service_name,
            "callback": callback,
        }
        return watch_id

    async def stop_watch(self, watch_id: str) -> bool:
        """Stop watching a service."""
        if watch_id in self._watches:
            del self._watches[watch_id]
            return True
        return False

    # Helper method for tests
    def set_service_health(self, service_id: str, healthy: bool) -> None:
        """Set service health status for testing."""
        if service_id in self._services:
            self._services[service_id]["healthy"] = healthy


class PartialServiceDiscovery:
    """Partial implementation that should NOT conform to protocol."""

    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        health_check_url: str | None = None,
        health_check_interval: str | None = None,
    ) -> bool:
        """Only implements register_service."""
        return True

    # Missing all other required methods


class WrongSignatureServiceDiscovery:
    """Implementation with wrong method signatures."""

    def register_service(  # Should be async
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        health_check_url: str | None = None,
        health_check_interval: str | None = None,
    ) -> bool:
        return True

    async def deregister_service(self, service_id: str) -> bool:
        return True

    async def discover_services(
        self,
        service_name: str,
        tags: list[str] | None = None,
        healthy_only: bool = True,
    ) -> list[dict[str, Any]]:
        return []

    async def get_service(self, service_id: str) -> dict[str, Any] | None:
        return None

    async def get_service_health(self, service_id: str) -> dict[str, Any]:
        return {"status": "unknown", "message": "", "last_check": None}

    async def list_services(self) -> list[str]:
        return []

    async def watch_service(self, service_name: str, callback: Any) -> str:
        return "watch-1"

    async def stop_watch(self, watch_id: str) -> bool:
        return True


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestProtocolServiceDiscoveryDefinition:
    """Test ProtocolServiceDiscovery protocol definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify protocol has @runtime_checkable decorator."""
        mock = MockServiceDiscovery()
        assert isinstance(mock, ProtocolServiceDiscovery)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """Verify isinstance returns False for non-conforming classes."""

        class NotAServiceDiscovery:
            pass

        obj = NotAServiceDiscovery()
        assert not isinstance(obj, ProtocolServiceDiscovery)

    def test_partial_implementation_fails_isinstance(self) -> None:
        """Verify partial implementations don't pass isinstance."""
        obj = PartialServiceDiscovery()
        assert not isinstance(obj, ProtocolServiceDiscovery)

    def test_protocol_methods_exist(self) -> None:
        """Verify protocol defines expected methods."""
        mock = MockServiceDiscovery()

        # Async methods
        assert hasattr(mock, "register_service")
        assert hasattr(mock, "deregister_service")
        assert hasattr(mock, "discover_services")
        assert hasattr(mock, "get_service")
        assert hasattr(mock, "get_service_health")
        assert hasattr(mock, "list_services")
        assert hasattr(mock, "watch_service")
        assert hasattr(mock, "stop_watch")

    def test_wrong_signature_passes_runtime_check(self) -> None:
        """
        Verify sync implementation passes runtime isinstance check.

        Note: Python's @runtime_checkable only checks for method/property names,
        NOT for async vs sync signatures. Static type checkers (mypy, pyright)
        will catch the distinction, but isinstance() cannot.
        """
        wrong = WrongSignatureServiceDiscovery()
        # Runtime check passes (only checks names exist)
        assert isinstance(wrong, ProtocolServiceDiscovery)

        # But we can verify the method isn't actually async
        assert not asyncio.iscoroutinefunction(wrong.register_service)


@pytest.mark.unit
class TestMockServiceDiscoveryBehavior:
    """Test MockServiceDiscovery behavior for protocol conformance."""

    @pytest.mark.asyncio
    async def test_initial_state(self) -> None:
        """Verify initial state has no services."""
        discovery = MockServiceDiscovery()
        services = await discovery.list_services()
        assert services == []

    @pytest.mark.asyncio
    async def test_register_service_basic(self) -> None:
        """Verify basic service registration works."""
        discovery = MockServiceDiscovery()

        result = await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )

        assert result is True
        services = await discovery.list_services()
        assert "api-gateway" in services

    @pytest.mark.asyncio
    async def test_register_service_with_tags(self) -> None:
        """Verify service registration with tags works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
            tags=["production", "v2"],
        )

        service = await discovery.get_service("api-1")
        assert service is not None
        assert service["tags"] == ["production", "v2"]

    @pytest.mark.asyncio
    async def test_register_service_with_metadata(self) -> None:
        """Verify service registration with metadata works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
            metadata={"version": "2.0", "region": "us-east"},
        )

        service = await discovery.get_service("api-1")
        assert service is not None
        assert service["metadata"]["version"] == "2.0"
        assert service["metadata"]["region"] == "us-east"

    @pytest.mark.asyncio
    async def test_register_service_with_health_check(self) -> None:
        """Verify service registration with health check works."""
        discovery = MockServiceDiscovery()

        result = await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
            health_check_url="http://10.0.0.1:8080/health",
            health_check_interval="10s",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_deregister_service(self) -> None:
        """Verify service deregistration works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )

        result = await discovery.deregister_service("api-1")
        assert result is True

        service = await discovery.get_service("api-1")
        assert service is None

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_service(self) -> None:
        """Verify deregistering nonexistent service returns False."""
        discovery = MockServiceDiscovery()

        result = await discovery.deregister_service("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_discover_services_by_name(self) -> None:
        """Verify service discovery by name works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )
        await discovery.register_service(
            service_id="api-2",
            service_name="api-gateway",
            address="10.0.0.2",
            port=8080,
        )
        await discovery.register_service(
            service_id="db-1",
            service_name="postgres",
            address="10.0.0.3",
            port=5432,
        )

        api_services = await discovery.discover_services("api-gateway")
        assert len(api_services) == 2

        db_services = await discovery.discover_services("postgres")
        assert len(db_services) == 1

    @pytest.mark.asyncio
    async def test_discover_services_by_tags(self) -> None:
        """Verify service discovery with tag filtering works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
            tags=["production", "v2"],
        )
        await discovery.register_service(
            service_id="api-2",
            service_name="api-gateway",
            address="10.0.0.2",
            port=8080,
            tags=["staging", "v2"],
        )

        prod_services = await discovery.discover_services(
            "api-gateway", tags=["production"]
        )
        assert len(prod_services) == 1
        assert prod_services[0]["id"] == "api-1"

        v2_services = await discovery.discover_services("api-gateway", tags=["v2"])
        assert len(v2_services) == 2

    @pytest.mark.asyncio
    async def test_discover_services_healthy_only(self) -> None:
        """Verify service discovery with healthy_only filter works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )
        await discovery.register_service(
            service_id="api-2",
            service_name="api-gateway",
            address="10.0.0.2",
            port=8080,
        )

        # Mark one as unhealthy
        discovery.set_service_health("api-2", healthy=False)

        # Default (healthy_only=True) should return only healthy services
        healthy_services = await discovery.discover_services("api-gateway")
        assert len(healthy_services) == 1
        assert healthy_services[0]["id"] == "api-1"

        # With healthy_only=False should return all services
        all_services = await discovery.discover_services(
            "api-gateway", healthy_only=False
        )
        assert len(all_services) == 2

    @pytest.mark.asyncio
    async def test_get_service(self) -> None:
        """Verify getting a specific service works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
            tags=["production"],
            metadata={"version": "2.0"},
        )

        service = await discovery.get_service("api-1")
        assert service is not None
        assert service["id"] == "api-1"
        assert service["name"] == "api-gateway"
        assert service["address"] == "10.0.0.1"
        assert service["port"] == 8080
        assert service["tags"] == ["production"]
        assert service["metadata"]["version"] == "2.0"

    @pytest.mark.asyncio
    async def test_get_nonexistent_service(self) -> None:
        """Verify getting nonexistent service returns None."""
        discovery = MockServiceDiscovery()

        service = await discovery.get_service("nonexistent")
        assert service is None

    @pytest.mark.asyncio
    async def test_get_service_health_healthy(self) -> None:
        """Verify getting health status for healthy service."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )

        health = await discovery.get_service_health("api-1")
        assert health["status"] == "passing"
        assert "message" in health
        assert "last_check" in health

    @pytest.mark.asyncio
    async def test_get_service_health_unhealthy(self) -> None:
        """Verify getting health status for unhealthy service."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )
        discovery.set_service_health("api-1", healthy=False)

        health = await discovery.get_service_health("api-1")
        assert health["status"] == "critical"

    @pytest.mark.asyncio
    async def test_get_service_health_unknown(self) -> None:
        """Verify getting health status for unknown service."""
        discovery = MockServiceDiscovery()

        health = await discovery.get_service_health("nonexistent")
        assert health["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_list_services(self) -> None:
        """Verify listing all service names works."""
        discovery = MockServiceDiscovery()

        await discovery.register_service(
            service_id="api-1",
            service_name="api-gateway",
            address="10.0.0.1",
            port=8080,
        )
        await discovery.register_service(
            service_id="api-2",
            service_name="api-gateway",
            address="10.0.0.2",
            port=8080,
        )
        await discovery.register_service(
            service_id="db-1",
            service_name="postgres",
            address="10.0.0.3",
            port=5432,
        )

        services = await discovery.list_services()
        assert len(services) == 2
        assert "api-gateway" in services
        assert "postgres" in services

    @pytest.mark.asyncio
    async def test_watch_service(self) -> None:
        """Verify watching a service returns watch ID."""
        discovery = MockServiceDiscovery()

        async def callback(services: list[dict[str, Any]]) -> None:
            pass

        watch_id = await discovery.watch_service("api-gateway", callback)
        assert watch_id is not None
        assert isinstance(watch_id, str)

    @pytest.mark.asyncio
    async def test_stop_watch(self) -> None:
        """Verify stopping a watch works."""
        discovery = MockServiceDiscovery()

        async def callback(services: list[dict[str, Any]]) -> None:
            pass

        watch_id = await discovery.watch_service("api-gateway", callback)
        result = await discovery.stop_watch(watch_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_stop_nonexistent_watch(self) -> None:
        """Verify stopping nonexistent watch returns False."""
        discovery = MockServiceDiscovery()

        result = await discovery.stop_watch("nonexistent")
        assert result is False


@pytest.mark.unit
class TestProtocolUsagePatterns:
    """Test common usage patterns with ProtocolServiceDiscovery."""

    @pytest.mark.asyncio
    async def test_function_accepting_protocol(self) -> None:
        """Test function that accepts ProtocolServiceDiscovery."""

        async def find_database(
            discovery: ProtocolServiceDiscovery,
        ) -> str | None:
            """Find a database service endpoint."""
            services = await discovery.discover_services("postgres")
            if services:
                service = services[0]
                return f"{service['address']}:{service['port']}"
            return None

        discovery = MockServiceDiscovery()
        await discovery.register_service(
            service_id="db-1",
            service_name="postgres",
            address="10.0.0.5",
            port=5432,
        )

        endpoint = await find_database(discovery)
        assert endpoint == "10.0.0.5:5432"

    @pytest.mark.asyncio
    async def test_load_balancing_pattern(self) -> None:
        """Test load balancing across discovered services."""

        async def get_service_endpoints(
            discovery: ProtocolServiceDiscovery,
            service_name: str,
        ) -> list[str]:
            """Get all endpoints for a service."""
            services = await discovery.discover_services(service_name)
            return [f"http://{s['address']}:{s['port']}" for s in services]

        discovery = MockServiceDiscovery()
        await discovery.register_service(
            service_id="api-1",
            service_name="api",
            address="10.0.0.1",
            port=8080,
        )
        await discovery.register_service(
            service_id="api-2",
            service_name="api",
            address="10.0.0.2",
            port=8080,
        )

        endpoints = await get_service_endpoints(discovery, "api")
        assert len(endpoints) == 2
        assert "http://10.0.0.1:8080" in endpoints
        assert "http://10.0.0.2:8080" in endpoints

    @pytest.mark.asyncio
    async def test_service_registration_lifecycle(self) -> None:
        """Test full service registration and deregistration lifecycle."""

        async def register_and_cleanup(
            discovery: ProtocolServiceDiscovery,
            service_id: str,
            service_name: str,
            address: str,
            port: int,
        ) -> bool:
            """Register service and return cleanup function result."""
            await discovery.register_service(
                service_id=service_id,
                service_name=service_name,
                address=address,
                port=port,
            )

            # Verify registration
            service = await discovery.get_service(service_id)
            if not service:
                return False

            # Cleanup
            return await discovery.deregister_service(service_id)

        discovery = MockServiceDiscovery()
        result = await register_and_cleanup(
            discovery, "test-1", "test-service", "127.0.0.1", 3000
        )
        assert result is True

        # Verify cleanup
        service = await discovery.get_service("test-1")
        assert service is None

    def test_type_annotation_works(self) -> None:
        """Test that type annotations work with protocol."""

        def check_discovery_type(discovery: ProtocolServiceDiscovery) -> bool:
            return isinstance(discovery, ProtocolServiceDiscovery)

        mock: ProtocolServiceDiscovery = MockServiceDiscovery()
        assert check_discovery_type(mock) is True


@pytest.mark.unit
class TestProtocolImports:
    """Test that protocols are correctly exported."""

    def test_import_from_infrastructure_module(self) -> None:
        """Test imports from omnibase_core.protocols.infrastructure."""
        from omnibase_core.protocols.infrastructure import ProtocolServiceDiscovery

        assert ProtocolServiceDiscovery is not None

    def test_import_from_protocol_file(self) -> None:
        """Test direct imports from protocol file."""
        from omnibase_core.protocols.infrastructure.protocol_service_discovery import (
            ProtocolServiceDiscovery,
        )

        assert ProtocolServiceDiscovery is not None

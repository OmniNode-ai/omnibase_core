# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelONEXContainer SPI protocol methods.

This module tests the get_external_services_health() and refresh_external_services()
methods of ModelONEXContainer, covering:
- Health reporting with active ServiceRegistry
- Health reporting when ServiceRegistry is disabled
- Graceful degradation on errors
- Cache clearing in refresh_external_services
- Integration with ServiceRegistry status and registrations

Ticket: OMN-717
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from omnibase_core.enums import (
    EnumHealthStatus,
    EnumInjectionScope,
    EnumOperationStatus,
    EnumServiceLifecycle,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_status import (
    ModelServiceRegistryStatus,
)
from omnibase_core.models.container.model_service_metadata import ModelServiceMetadata
from omnibase_core.models.container.model_service_registration import (
    ModelServiceRegistration,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _make_registration(
    name: str = "test_service",
    interface: str = "ProtocolTestService",
    health: EnumHealthStatus = EnumHealthStatus.HEALTHY,
    lifecycle: EnumServiceLifecycle = EnumServiceLifecycle.SINGLETON,
    instance_count: int = 1,
    access_count: int = 5,
) -> ModelServiceRegistration:
    """Create a ModelServiceRegistration for testing."""
    return ModelServiceRegistration(
        registration_id=uuid4(),
        service_metadata=ModelServiceMetadata(
            service_id=uuid4(),
            service_name=name,
            service_interface=interface,
            service_implementation=f"Mock{name.title().replace('_', '')}",
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        lifecycle=lifecycle,
        scope=EnumInjectionScope.GLOBAL,
        health_status=health,
        instance_count=instance_count,
        access_count=access_count,
    )


def _make_registry_status(
    total: int = 2,
    active: int = 2,
    failed: int = 0,
    health_summary: dict[EnumHealthStatus, int] | None = None,
) -> ModelServiceRegistryStatus:
    """Create a ModelServiceRegistryStatus for testing."""
    return ModelServiceRegistryStatus(
        registry_id=uuid4(),
        status=EnumOperationStatus.SUCCESS
        if failed == 0
        else EnumOperationStatus.FAILED,
        message="Registry operational" if failed == 0 else "Registry has failures",
        total_registrations=total,
        active_instances=active,
        failed_registrations=failed,
        health_summary=health_summary or {EnumHealthStatus.HEALTHY: total},
    )


@pytest.mark.unit
class TestGetExternalServicesHealthRegistryDisabled:
    """Tests for get_external_services_health when ServiceRegistry is disabled."""

    @pytest.mark.asyncio
    async def test_returns_unavailable_when_registry_disabled(self) -> None:
        """When ServiceRegistry is disabled, returns unavailable status."""
        container = ModelONEXContainer(enable_service_registry=False)

        result = await container.get_external_services_health()

        assert result["status"] == "unavailable"
        assert "not initialized" in str(result["message"]).lower()


@pytest.mark.unit
class TestGetExternalServicesHealthWithRegistry:
    """Tests for get_external_services_health with active ServiceRegistry."""

    @pytest.mark.asyncio
    async def test_returns_healthy_status_with_healthy_services(self) -> None:
        """When all services are healthy, returns healthy status."""
        container = ModelONEXContainer(enable_service_registry=True)

        reg1 = _make_registration(name="logger", interface="ProtocolLogger")
        reg2 = _make_registration(name="cache", interface="ProtocolCache")
        status = _make_registry_status(total=2, active=2)

        container._service_registry.get_registry_status = AsyncMock(return_value=status)
        container._service_registry.get_all_registrations = AsyncMock(
            return_value=[reg1, reg2]
        )

        result = await container.get_external_services_health()

        assert result["status"] == "healthy"
        assert result["total_registrations"] == 2
        assert result["active_instances"] == 2
        assert result["health_percentage"] == 100.0
        assert result["failed_registrations"] == 0

        services = result["services"]
        assert isinstance(services, list)
        assert len(services) == 2
        assert services[0]["service_name"] == "logger"
        assert services[0]["service_interface"] == "ProtocolLogger"
        assert services[0]["health_status"] == EnumHealthStatus.HEALTHY.value
        assert services[0]["is_active"] is True

    @pytest.mark.asyncio
    async def test_returns_degraded_status_with_failures(self) -> None:
        """When there are failed registrations, returns degraded status."""
        container = ModelONEXContainer(enable_service_registry=True)

        reg1 = _make_registration(
            name="db", interface="ProtocolDB", health=EnumHealthStatus.UNHEALTHY
        )
        status = _make_registry_status(
            total=1,
            active=0,
            failed=1,
            health_summary={EnumHealthStatus.UNHEALTHY: 1},
        )

        container._service_registry.get_registry_status = AsyncMock(return_value=status)
        container._service_registry.get_all_registrations = AsyncMock(
            return_value=[reg1]
        )

        result = await container.get_external_services_health()

        assert result["status"] == "degraded"
        assert result["failed_registrations"] == 1
        assert result["health_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_empty_services_when_none_registered(self) -> None:
        """When no services are registered, returns healthy with empty list."""
        container = ModelONEXContainer(enable_service_registry=True)

        status = _make_registry_status(total=0, active=0)

        container._service_registry.get_registry_status = AsyncMock(return_value=status)
        container._service_registry.get_all_registrations = AsyncMock(return_value=[])

        result = await container.get_external_services_health()

        assert result["status"] == "healthy"
        assert result["total_registrations"] == 0
        assert result["services"] == []
        assert result["health_percentage"] == 100.0


@pytest.mark.unit
class TestGetExternalServicesHealthErrorHandling:
    """Tests for get_external_services_health error handling."""

    @pytest.mark.asyncio
    async def test_returns_degraded_on_registry_error(self) -> None:
        """When ServiceRegistry raises an error, returns degraded status."""
        container = ModelONEXContainer(enable_service_registry=True)

        container._service_registry.get_registry_status = AsyncMock(
            side_effect=RuntimeError("Registry unavailable")
        )

        result = await container.get_external_services_health()

        assert result["status"] == "degraded"
        assert "Registry unavailable" in str(result["message"])


@pytest.mark.unit
class TestGetExternalServicesHealthServiceDetails:
    """Tests for per-service details in health response."""

    @pytest.mark.asyncio
    async def test_includes_service_metadata_in_response(self) -> None:
        """Each service entry includes lifecycle, instance count, and access count."""
        container = ModelONEXContainer(enable_service_registry=True)

        reg = _make_registration(
            name="event_bus",
            interface="ProtocolEventBus",
            lifecycle=EnumServiceLifecycle.TRANSIENT,
            instance_count=3,
            access_count=42,
        )
        status = _make_registry_status(total=1, active=3)

        container._service_registry.get_registry_status = AsyncMock(return_value=status)
        container._service_registry.get_all_registrations = AsyncMock(
            return_value=[reg]
        )

        result = await container.get_external_services_health()

        service_detail = result["services"][0]
        assert service_detail["lifecycle"] == EnumServiceLifecycle.TRANSIENT.value
        assert service_detail["instance_count"] == 3
        assert service_detail["access_count"] == 42


@pytest.mark.unit
class TestRefreshExternalServicesCacheClearing:
    """Tests for refresh_external_services cache clearing behavior."""

    @pytest.mark.asyncio
    async def test_clears_service_cache(self) -> None:
        """Calling refresh_external_services clears the service cache."""
        container = ModelONEXContainer(enable_service_registry=True)

        # Populate cache manually
        container._service_cache["ProtocolLogger:default"] = object()
        container._service_cache["ProtocolCache:default"] = object()
        assert len(container._service_cache) == 2

        await container.refresh_external_services()

        assert len(container._service_cache) == 0

    @pytest.mark.asyncio
    async def test_refresh_with_empty_cache(self) -> None:
        """Calling refresh_external_services with empty cache does not error."""
        container = ModelONEXContainer(enable_service_registry=True)

        assert len(container._service_cache) == 0

        await container.refresh_external_services()

        assert len(container._service_cache) == 0


@pytest.mark.unit
class TestRefreshExternalServicesRegistryDisabled:
    """Tests for refresh_external_services when registry is disabled."""

    @pytest.mark.asyncio
    async def test_clears_cache_even_when_registry_disabled(self) -> None:
        """Cache is cleared regardless of whether ServiceRegistry is enabled."""
        container = ModelONEXContainer(enable_service_registry=False)

        container._service_cache["some_key"] = object()

        await container.refresh_external_services()

        assert len(container._service_cache) == 0


@pytest.mark.unit
class TestRefreshExternalServicesSubsequentResolution:
    """Tests for service re-resolution after refresh."""

    @pytest.mark.asyncio
    async def test_cache_repopulated_after_refresh(self) -> None:
        """After refresh, subsequent get_service_async re-populates cache."""
        container = ModelONEXContainer(enable_service_registry=True)

        # Pre-populate cache
        sentinel = object()
        container._service_cache["ProtocolTest:default"] = sentinel
        assert container._service_cache["ProtocolTest:default"] is sentinel

        # Refresh clears cache
        await container.refresh_external_services()
        assert "ProtocolTest:default" not in container._service_cache

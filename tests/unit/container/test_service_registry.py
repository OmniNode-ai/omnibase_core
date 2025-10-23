"""Unit tests for ServiceRegistry implementation."""

from uuid import UUID

import pytest

from omnibase_core.container.service_registry import ServiceRegistry
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)


# Test Protocol Interface
class ITestService:
    """Test service interface."""

    def execute(self) -> str:
        """Execute service logic."""


# Test Implementation
class TestServiceImplementation(ITestService):
    """Test service implementation."""

    def __init__(self, name: str = "test") -> None:
        """Initialize test service."""
        self.name = name
        self.execution_count = 0

    def execute(self) -> str:
        """Execute service logic."""
        self.execution_count += 1
        return f"Executed {self.name} (count: {self.execution_count})"


class TestServiceRegistry:
    """Test suite for ServiceRegistry."""

    @pytest.fixture
    def registry(self) -> ServiceRegistry:
        """Create a test registry instance."""
        config = create_default_registry_config()
        return ServiceRegistry(config)

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry: ServiceRegistry) -> None:
        """Test registry initializes correctly."""
        assert registry is not None
        assert registry.config is not None
        assert registry.config.registry_name == "omnibase_core_registry"
        assert registry.config.lazy_loading_enabled is True
        assert registry.config.circular_dependency_detection is True

    @pytest.mark.asyncio
    async def test_register_instance(self, registry: ServiceRegistry) -> None:
        """Test registering service instance."""
        # Create test service
        test_service = TestServiceImplementation("test1")

        # Register instance
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
            metadata={"description": "Test service instance"},
        )

        # Verify registration
        assert registration_id is not None
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.service_metadata.service_name == "TestServiceImplementation"
        assert registration.lifecycle == "singleton"
        assert registration.scope == "global"
        assert registration.registration_status == "registered"

    @pytest.mark.asyncio
    async def test_resolve_service_by_interface(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolving service by interface."""
        # Register service
        test_service = TestServiceImplementation("test2")
        await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Resolve service
        resolved_service = await registry.resolve_service(ITestService)

        # Verify resolution
        assert resolved_service is not None
        assert isinstance(resolved_service, TestServiceImplementation)
        assert resolved_service.name == "test2"

        # Test execution
        result = resolved_service.execute()
        assert "Executed test2" in result
        assert "count: 1" in result

    @pytest.mark.asyncio
    async def test_singleton_lifecycle(self, registry: ServiceRegistry) -> None:
        """Test singleton lifecycle returns same instance."""
        # Register singleton
        test_service = TestServiceImplementation("singleton")
        await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Resolve multiple times
        instance1 = await registry.resolve_service(ITestService)
        instance2 = await registry.resolve_service(ITestService)

        # Verify same instance
        assert instance1 is instance2

        # Verify state is shared
        instance1.execute()
        assert instance2.execution_count == 1

    @pytest.mark.asyncio
    async def test_resolve_service_not_found(self, registry: ServiceRegistry) -> None:
        """Test resolving non-existent service raises error."""

        class IUnregisteredService:
            """Unregistered service interface."""

        with pytest.raises(ModelOnexError):
            await registry.resolve_service(IUnregisteredService)

    @pytest.mark.asyncio
    async def test_try_resolve_service_returns_none(
        self, registry: ServiceRegistry
    ) -> None:
        """Test try_resolve returns None for non-existent service."""

        class IUnregisteredService:
            """Unregistered service interface."""

        result = await registry.try_resolve_service(IUnregisteredService)
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_service(self, registry: ServiceRegistry) -> None:
        """Test unregistering service."""
        # Register service
        test_service = TestServiceImplementation("test3")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Verify registration exists
        registration = await registry.get_registration(registration_id)
        assert registration is not None

        # Unregister service
        result = await registry.unregister_service(registration_id)
        assert result is True

        # Verify registration removed
        registration_after = await registry.get_registration(registration_id)
        assert registration_after is None

        # Verify can't resolve anymore
        with pytest.raises(ModelOnexError):
            await registry.resolve_service(ITestService)

    @pytest.mark.asyncio
    async def test_get_all_registrations(self, registry: ServiceRegistry) -> None:
        """Test getting all registrations."""
        # Register multiple services
        service1 = TestServiceImplementation("service1")
        service2 = TestServiceImplementation("service2")

        await registry.register_instance(
            interface=ITestService,
            instance=service1,
            scope="global",
        )
        await registry.register_instance(
            interface=ITestService,
            instance=service2,
            scope="global",
        )

        # Get all registrations
        all_registrations = await registry.get_all_registrations()

        # Verify count
        assert len(all_registrations) == 2

        # Verify all are active
        for registration in all_registrations:
            assert registration.is_active() is True

    @pytest.mark.asyncio
    async def test_get_registrations_by_interface(
        self, registry: ServiceRegistry
    ) -> None:
        """Test getting registrations by interface."""
        # Register services
        service1 = TestServiceImplementation("service1")
        await registry.register_instance(
            interface=ITestService,
            instance=service1,
            scope="global",
        )

        # Get by interface
        registrations = await registry.get_registrations_by_interface(ITestService)

        # Verify
        assert len(registrations) >= 1
        assert registrations[0].service_metadata.service_interface == "ITestService"

    @pytest.mark.asyncio
    async def test_get_active_instances(self, registry: ServiceRegistry) -> None:
        """Test getting active instances."""
        # Register service
        test_service = TestServiceImplementation("test4")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Get active instances
        instances = await registry.get_active_instances(registration_id)

        # Verify
        assert len(instances) == 1
        assert instances[0].instance is test_service
        assert instances[0].is_active() is True

    @pytest.mark.asyncio
    async def test_dispose_instances(self, registry: ServiceRegistry) -> None:
        """Test disposing instances."""
        # Register service
        test_service = TestServiceImplementation("test5")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Dispose instances
        disposed_count = await registry.dispose_instances(registration_id)

        # Verify
        assert disposed_count == 1

        # Verify instances are disposed
        instances = await registry.get_active_instances(registration_id)
        assert all(inst.is_disposed for inst in instances)

    @pytest.mark.asyncio
    async def test_get_registry_status(self, registry: ServiceRegistry) -> None:
        """Test getting registry status."""
        # Register services
        service1 = TestServiceImplementation("service1")
        service2 = TestServiceImplementation("service2")

        await registry.register_instance(
            interface=ITestService,
            instance=service1,
            scope="global",
        )
        await registry.register_instance(
            interface=ITestService,
            instance=service2,
            scope="global",
        )

        # Get status
        status = await registry.get_registry_status()

        # Verify status
        assert status is not None
        assert isinstance(status.registry_id, UUID)
        assert status.status == "success"  # Should be success with no failures
        assert status.total_registrations >= 2
        assert status.active_instances >= 2
        assert status.failed_registrations == 0
        assert status.circular_dependencies == 0
        assert status.is_healthy() is True
        assert status.get_health_percentage() >= 0.0

    @pytest.mark.asyncio
    async def test_resolve_all_services(self, registry: ServiceRegistry) -> None:
        """Test resolving all services for interface."""
        # Register multiple services
        service1 = TestServiceImplementation("service1")
        service2 = TestServiceImplementation("service2")

        await registry.register_instance(
            interface=ITestService,
            instance=service1,
            scope="global",
        )
        await registry.register_instance(
            interface=ITestService,
            instance=service2,
            scope="global",
        )

        # Resolve all
        all_services = await registry.resolve_all_services(ITestService)

        # Verify
        assert len(all_services) >= 2
        assert all(isinstance(svc, TestServiceImplementation) for svc in all_services)

    @pytest.mark.asyncio
    async def test_update_service_configuration(
        self, registry: ServiceRegistry
    ) -> None:
        """Test updating service configuration."""
        # Register service
        test_service = TestServiceImplementation("test6")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
            metadata={"version": "1.0"},
        )

        # Update configuration
        result = await registry.update_service_configuration(
            registration_id,
            {"version": "2.0", "updated": True},
        )

        # Verify
        assert result is True

        # Check updated configuration
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.service_metadata.configuration["version"] == "2.0"
        assert registration.service_metadata.configuration["updated"] is True
        assert registration.service_metadata.last_modified_at is not None

    @pytest.mark.asyncio
    async def test_validate_registration(self, registry: ServiceRegistry) -> None:
        """Test validating registration."""
        # Register service
        test_service = TestServiceImplementation("test7")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Get and validate registration
        registration = await registry.get_registration(registration_id)
        assert registration is not None

        is_valid = await registry.validate_registration(registration)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_registration_access_tracking(
        self, registry: ServiceRegistry
    ) -> None:
        """Test registration access count tracking."""
        # Register service
        test_service = TestServiceImplementation("test8")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Get initial access count
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        initial_access_count = registration.access_count

        # Resolve service multiple times
        await registry.resolve_service(ITestService)
        await registry.resolve_service(ITestService)

        # Verify access count increased
        registration_after = await registry.get_registration(registration_id)
        assert registration_after is not None
        assert registration_after.access_count > initial_access_count


class TestContainerIntegration:
    """Test container integration with ServiceRegistry."""

    @pytest.mark.asyncio
    async def test_container_has_service_registry(self) -> None:
        """Test that container initializes with service registry."""
        from omnibase_core.models.container.model_onex_container import (
            create_model_onex_container,
        )

        container = await create_model_onex_container(enable_service_registry=True)

        # Verify registry exists
        assert container.service_registry is not None

    @pytest.mark.asyncio
    async def test_container_service_resolution_with_registry(self) -> None:
        """Test that container can resolve services via registry."""
        from omnibase_core.models.container.model_onex_container import (
            create_model_onex_container,
        )

        container = await create_model_onex_container(enable_service_registry=True)

        # Register a test service in the registry
        test_service = TestServiceImplementation("container_test")
        await container.service_registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        # Resolve via container
        resolved = await container.get_service_async(ITestService)

        # Verify
        assert resolved is not None
        assert isinstance(resolved, TestServiceImplementation)
        assert resolved.name == "container_test"

    @pytest.mark.asyncio
    async def test_container_without_service_registry(self) -> None:
        """Test container can work without service registry."""
        from omnibase_core.models.container.model_onex_container import (
            create_model_onex_container,
        )

        container = await create_model_onex_container(enable_service_registry=False)

        # Verify registry is None
        assert container.service_registry is None

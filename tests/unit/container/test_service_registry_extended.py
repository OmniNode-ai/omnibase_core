"""Extended unit tests for ServiceRegistry - covering uncovered paths."""

from uuid import UUID, uuid4

import pytest

from omnibase_core.container.service_registry import ServiceRegistry
from omnibase_core.models.errors.model_onex_error import ModelOnexError


# Test Protocol Interface
class ITestService:
    """Test service interface."""

    def execute(self) -> str:
        """Execute service logic."""


# Mock Implementation (not a test class - prefix avoids pytest collection)
class MockServiceImplementation(ITestService):
    """Mock service implementation for testing."""

    def __init__(self, name: str = "test") -> None:
        """Initialize mock service."""
        self.name = name
        self.execution_count = 0

    def execute(self) -> str:
        """Execute service logic."""
        self.execution_count += 1
        return f"Executed {self.name} (count: {self.execution_count})"


class IAnotherService:
    """Another test service interface."""

    def process(self) -> str:
        """Process service logic."""


class AnotherServiceImplementation(IAnotherService):
    """Another test service implementation."""

    def __init__(self, name: str = "another") -> None:
        """Initialize another service."""
        self.name = name

    def process(self) -> str:
        """Process service logic."""
        return f"Processed {self.name}"


class TestServiceRegistryExtended:
    """Extended test suite for ServiceRegistry covering uncovered paths.

    Note:
        Registry fixtures (registry, non_lazy_registry) are provided by conftest.py
        to avoid duplication across test files.
    """

    # ===== register_service Tests (Lines 118-209) =====

    @pytest.mark.asyncio
    async def test_register_service_with_lazy_loading(
        self, registry: ServiceRegistry
    ) -> None:
        """Test register_service with lazy loading enabled (default)."""
        registration_id = await registry.register_service(
            interface=ITestService,
            implementation=MockServiceImplementation,
            lifecycle="singleton",
            scope="global",
            configuration={"env": "test"},
        )

        # Verify registration
        assert isinstance(registration_id, UUID)
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.lifecycle == "singleton"
        assert registration.scope == "global"
        assert registration.service_metadata.configuration == {"env": "test"}

        # Verify no instance created yet (lazy loading)
        instances = await registry.get_active_instances(registration_id)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_register_service_non_lazy_singleton(
        self, non_lazy_registry: ServiceRegistry
    ) -> None:
        """Test register_service with lazy_loading_enabled=False (Lines 184-187)."""
        registration_id = await non_lazy_registry.register_service(
            interface=ITestService,
            implementation=MockServiceImplementation,
            lifecycle="singleton",
            scope="global",
        )

        # Verify registration
        assert isinstance(registration_id, UUID)

        # Verify instance created immediately (non-lazy)
        instances = await non_lazy_registry.get_active_instances(registration_id)
        assert len(instances) == 1
        assert isinstance(instances[0].instance, MockServiceImplementation)

    @pytest.mark.asyncio
    async def test_register_service_with_transient_lazy(
        self, registry: ServiceRegistry
    ) -> None:
        """Test register_service with transient lifecycle (lazy loading)."""
        registration_id = await registry.register_service(
            interface=ITestService,
            implementation=MockServiceImplementation,
            lifecycle="transient",
            scope="request",
        )

        # Verify registration
        assert isinstance(registration_id, UUID)
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.lifecycle == "transient"

        # No instance created with lazy loading for transient
        instances = await registry.get_active_instances(registration_id)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_register_service_error_handling(
        self, registry: ServiceRegistry
    ) -> None:
        """Test register_service error handling (Lines 201-208)."""

        # Create a class that raises error on instantiation
        class FailingService:
            def __init__(self) -> None:
                raise RuntimeError("Initialization failed")

        # Disable lazy loading to trigger instantiation
        registry._config.lazy_loading_enabled = False

        # Should catch exception and wrap in ModelOnexError
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.register_service(
                interface=ITestService,
                implementation=FailingService,
                lifecycle="singleton",
                scope="global",
            )

        # Verify failed registration count increased
        status = await registry.get_registry_status()
        assert status.failed_registrations == 1

    # ===== register_instance Error Handling (Lines 280-287) =====

    @pytest.mark.asyncio
    async def test_register_instance_error_handling(
        self, registry: ServiceRegistry
    ) -> None:
        """Test register_instance error handling path (Lines 280-287)."""

        # Force an error by passing invalid interface type
        # We'll mock this by monkeypatching the _store_instance method
        original_store = registry._store_instance

        async def failing_store(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("Storage failed")

        registry._store_instance = failing_store  # type: ignore[method-assign]

        with pytest.raises(ModelOnexError) as exc_info:
            await registry.register_instance(
                interface=ITestService,
                instance=MockServiceImplementation("test"),
                scope="global",
            )

        # Verify error message
        assert "Instance registration failed" in str(exc_info.value)

        # Verify failed registration count increased
        status = await registry.get_registry_status()
        assert status.failed_registrations == 1

        # Restore original method
        registry._store_instance = original_store  # type: ignore[method-assign]

    # ===== register_factory Not Implemented (Lines 289-315) =====

    @pytest.mark.asyncio
    async def test_register_factory_not_implemented(
        self, registry: ServiceRegistry
    ) -> None:
        """Test register_factory raises not implemented error (Lines 311-315)."""
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.register_factory(
                interface=ITestService,
                factory=lambda: MockServiceImplementation(),
                lifecycle="transient",
                scope="global",
            )

        assert "Factory registration not yet implemented" in str(exc_info.value)

    # ===== unregister_service Edge Cases (Lines 327-351) =====

    @pytest.mark.asyncio
    async def test_unregister_service_not_found(
        self, registry: ServiceRegistry
    ) -> None:
        """Test unregister_service returns False for non-existent ID (Lines 327-328)."""
        fake_id = uuid4()
        result = await registry.unregister_service(fake_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_unregister_service_full_cleanup(
        self, registry: ServiceRegistry
    ) -> None:
        """Test unregister_service performs full cleanup (Lines 330-351)."""
        # Register two services with same interface
        service1 = MockServiceImplementation("service1")
        service2 = MockServiceImplementation("service2")

        reg_id_1 = await registry.register_instance(
            interface=ITestService,
            instance=service1,
            scope="global",
        )
        reg_id_2 = await registry.register_instance(
            interface=ITestService,
            instance=service2,
            scope="global",
        )

        # Verify both in interface map
        registrations = await registry.get_registrations_by_interface(ITestService)
        assert len(registrations) == 2

        # Unregister first service
        result = await registry.unregister_service(reg_id_1)
        assert result is True

        # Verify cleanup:
        # - Registration removed
        assert await registry.get_registration(reg_id_1) is None
        # - Interface map updated (still has one registration)
        registrations_after = await registry.get_registrations_by_interface(
            ITestService
        )
        assert len(registrations_after) == 1
        # - Instances disposed
        instances = await registry.get_active_instances(reg_id_1)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_unregister_service_removes_empty_interface_map(
        self, registry: ServiceRegistry
    ) -> None:
        """Test unregister removes interface_map entry when empty (Lines 342-343)."""
        # Register single service
        service = MockServiceImplementation("service")
        reg_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Verify interface map has entry
        registrations = await registry.get_registrations_by_interface(ITestService)
        assert len(registrations) == 1

        # Unregister
        await registry.unregister_service(reg_id)

        # Verify interface map entry removed (empty list removed)
        registrations_after = await registry.get_registrations_by_interface(
            ITestService
        )
        assert len(registrations_after) == 0

    # ===== resolve_service Empty Registration List (Lines 396-401) =====

    @pytest.mark.asyncio
    async def test_resolve_service_empty_registration_list(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolve_service with empty registration_ids list (Lines 396-401)."""
        # Manually create an empty interface map entry (edge case)
        registry._interface_map["IFakeService"] = []

        # Mock interface with __name__
        class IFakeService:
            pass

        # Should raise error for empty list
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.resolve_service(IFakeService)

        assert "No active registrations" in str(exc_info.value)

    # ===== resolve_named_service (Lines 462-475) =====

    @pytest.mark.asyncio
    async def test_resolve_named_service_success(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolve_named_service happy path (Lines 462-475)."""
        # Register service
        service = MockServiceImplementation("named_service")
        await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Resolve by name
        resolved = await registry.resolve_named_service(
            interface=ITestService,
            name="MockServiceImplementation",
        )

        # Verify
        assert resolved is not None
        assert isinstance(resolved, MockServiceImplementation)

    @pytest.mark.asyncio
    async def test_resolve_named_service_not_found(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolve_named_service raises error for unknown name (Lines 462-467)."""
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.resolve_named_service(
                interface=ITestService,
                name="NonExistentService",
            )

        assert "No service registered with name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_named_service_with_scope_override(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolve_named_service with scope override (Line 473)."""
        # Register service
        service = MockServiceImplementation("scoped_service")
        await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Resolve with scope override (should still work)
        resolved = await registry.resolve_named_service(
            interface=ITestService,
            name="MockServiceImplementation",
            scope="request",
        )

        assert resolved is not None

    # ===== get_active_instances Without registration_id (Lines 593-599) =====

    @pytest.mark.asyncio
    async def test_get_active_instances_all(self, registry: ServiceRegistry) -> None:
        """Test get_active_instances returns all instances when no ID provided (Lines 595-599)."""
        # Register multiple services
        service1 = MockServiceImplementation("service1")
        service2 = AnotherServiceImplementation("service2")

        await registry.register_instance(
            interface=ITestService,
            instance=service1,
            scope="global",
        )
        await registry.register_instance(
            interface=IAnotherService,
            instance=service2,
            scope="global",
        )

        # Get all instances (no registration_id)
        all_instances = await registry.get_active_instances(registration_id=None)

        # Verify we got instances from both registrations
        assert len(all_instances) >= 2
        instance_objects = [inst.instance for inst in all_instances]
        assert service1 in instance_objects
        assert service2 in instance_objects

    # ===== dispose_instances Edge Cases (Lines 614-615) =====

    @pytest.mark.asyncio
    async def test_dispose_instances_not_found(self, registry: ServiceRegistry) -> None:
        """Test dispose_instances returns 0 for non-existent registration (Lines 614-615)."""
        fake_id = uuid4()
        disposed_count = await registry.dispose_instances(fake_id)
        assert disposed_count == 0

    @pytest.mark.asyncio
    async def test_dispose_instances_with_scope_filter(
        self, registry: ServiceRegistry
    ) -> None:
        """Test dispose_instances with scope filter (Lines 621-623)."""
        # Register service
        service = MockServiceImplementation("scoped")
        reg_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Dispose with wrong scope (should not dispose)
        disposed_count = await registry.dispose_instances(reg_id, scope="request")
        assert disposed_count == 0

        # Dispose with correct scope (should dispose)
        disposed_count = await registry.dispose_instances(reg_id, scope="global")
        assert disposed_count == 1

    # ===== Performance Metrics Tracking (Lines 411-419) =====

    @pytest.mark.asyncio
    async def test_resolve_service_tracks_performance_metrics(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolve_service tracks performance metrics (Lines 417-419)."""
        # Register service
        service = MockServiceImplementation("perf_test")
        await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Resolve service (triggers performance tracking)
        await registry.resolve_service(ITestService)

        # Verify metrics recorded
        status = await registry.get_registry_status()
        assert status.average_resolution_time_ms is not None
        assert status.average_resolution_time_ms >= 0.0

    # ===== validate_service_health Not Implemented (Lines 733-747) =====

    @pytest.mark.asyncio
    async def test_validate_service_health_not_implemented(
        self, registry: ServiceRegistry
    ) -> None:
        """Test validate_service_health raises not implemented (Lines 743-747)."""
        fake_id = uuid4()
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.validate_service_health(fake_id)

        assert "Service health validation not yet fully implemented" in str(
            exc_info.value
        )

    # ===== update_service_configuration Not Found (Lines 762-763) =====

    @pytest.mark.asyncio
    async def test_update_service_configuration_not_found(
        self, registry: ServiceRegistry
    ) -> None:
        """Test update_service_configuration returns False for unknown ID (Lines 762-763)."""
        fake_id = uuid4()
        result = await registry.update_service_configuration(
            fake_id, {"new_config": "value"}
        )
        assert result is False

    # ===== create_injection_scope Not Implemented (Lines 771-791) =====

    @pytest.mark.asyncio
    async def test_create_injection_scope_not_implemented(
        self, registry: ServiceRegistry
    ) -> None:
        """Test create_injection_scope raises not implemented (Lines 787-791)."""
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.create_injection_scope(
                scope_name="test_scope", parent_scope=None
            )

        assert "Injection scope creation not yet implemented" in str(exc_info.value)

    # ===== dispose_injection_scope Not Implemented (Lines 793-810) =====

    @pytest.mark.asyncio
    async def test_dispose_injection_scope_not_implemented(
        self, registry: ServiceRegistry
    ) -> None:
        """Test dispose_injection_scope raises not implemented (Lines 806-810)."""
        fake_id = uuid4()
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.dispose_injection_scope(fake_id)

        assert "Injection scope disposal not yet implemented" in str(exc_info.value)

    # ===== get_injection_context Returns None (Lines 812-822) =====

    @pytest.mark.asyncio
    async def test_get_injection_context_returns_none(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_injection_context returns None (Line 822)."""
        fake_id = uuid4()
        result = await registry.get_injection_context(fake_id)
        assert result is None

    # ===== detect_circular_dependencies Returns Empty (Lines 646-659) =====

    @pytest.mark.asyncio
    async def test_detect_circular_dependencies_returns_empty(
        self, registry: ServiceRegistry
    ) -> None:
        """Test detect_circular_dependencies returns empty list (Line 659)."""
        # Register service
        service = MockServiceImplementation("test")
        reg_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        registration = await registry.get_registration(reg_id)
        assert registration is not None

        # Should return empty list (not implemented in v1.0)
        circular_deps = await registry.detect_circular_dependencies(registration)
        assert circular_deps == []

    # ===== get_dependency_graph Returns None (Lines 661-671) =====

    @pytest.mark.asyncio
    async def test_get_dependency_graph_returns_none(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_dependency_graph returns None (Line 671)."""
        fake_id = uuid4()
        result = await registry.get_dependency_graph(fake_id)
        assert result is None

    # ===== _resolve_by_lifecycle Error Paths (Lines 855-895) =====

    @pytest.mark.asyncio
    async def test_resolve_by_lifecycle_singleton_not_found(
        self, registry: ServiceRegistry
    ) -> None:
        """Test _resolve_by_lifecycle raises error for missing singleton (Lines 876-880)."""
        # Register service without instance (using register_service with lazy loading)
        reg_id = await registry.register_service(
            interface=ITestService,
            implementation=MockServiceImplementation,
            lifecycle="singleton",
            scope="global",
        )

        # Try to resolve (no instance exists, lazy loading)
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.resolve_service(ITestService)

        assert "Singleton instance not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_by_lifecycle_transient_not_supported(
        self, registry: ServiceRegistry
    ) -> None:
        """Test _resolve_by_lifecycle raises error for transient lifecycle (Lines 882-889)."""
        # Register transient service (lazy loading)
        reg_id = await registry.register_service(
            interface=ITestService,
            implementation=MockServiceImplementation,
            lifecycle="transient",
            scope="request",
        )

        # Try to resolve transient (not supported without factory)
        with pytest.raises(ModelOnexError) as exc_info:
            await registry.resolve_service(ITestService)

        assert "Transient lifecycle not yet supported" in str(exc_info.value)

    # ===== get_registry_status Edge Cases =====

    @pytest.mark.asyncio
    async def test_get_registry_status_with_failures(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_registry_status shows 'failed' status with failures (Lines 713-714)."""
        # Register a service first so registry is not empty
        service = MockServiceImplementation("service")
        await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Simulate failed registration
        registry._failed_registrations = 5

        status = await registry.get_registry_status()
        assert status.failed_registrations == 5
        assert status.status == "failed"

    @pytest.mark.asyncio
    async def test_get_registry_status_empty_registry(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_registry_status shows 'pending' for empty registry (Lines 715-716)."""
        # Fresh registry with no registrations
        status = await registry.get_registry_status()

        assert status.total_registrations == 0
        assert status.status == "pending"

    @pytest.mark.asyncio
    async def test_get_registry_status_lifecycle_and_scope_distribution(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_registry_status calculates distributions correctly (Lines 681-698)."""
        # Register services with different lifecycles and scopes
        service1 = MockServiceImplementation("service1")
        service2 = AnotherServiceImplementation("service2")

        await registry.register_instance(
            interface=ITestService, instance=service1, scope="global"
        )
        await registry.register_instance(
            interface=IAnotherService, instance=service2, scope="request"
        )

        status = await registry.get_registry_status()

        # Verify distributions
        assert "singleton" in status.lifecycle_distribution
        assert status.lifecycle_distribution["singleton"] == 2
        assert "global" in status.scope_distribution
        assert "request" in status.scope_distribution

    # ===== Properties Coverage =====

    @pytest.mark.asyncio
    async def test_registry_properties(self, registry: ServiceRegistry) -> None:
        """Test registry property accessors (Lines 103-116)."""
        # Test config property
        assert registry.config is not None
        assert registry.config.registry_name == "omnibase_core_registry"

        # Test validator property (returns None in v1.0)
        assert registry.validator is None

        # Test factory property (returns None in v1.0)
        assert registry.factory is None

    # ===== resolve_all_services Empty Case =====

    @pytest.mark.asyncio
    async def test_resolve_all_services_empty(self, registry: ServiceRegistry) -> None:
        """Test resolve_all_services returns empty list for unregistered interface (Lines 496-497)."""

        class IUnregisteredService:
            pass

        services = await registry.resolve_all_services(IUnregisteredService)
        assert services == []

    # ===== get_registrations_by_interface Empty Case =====

    @pytest.mark.asyncio
    async def test_get_registrations_by_interface_empty(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_registrations_by_interface returns empty for unregistered interface (Lines 561-562)."""

        class IUnregisteredService:
            pass

        registrations = await registry.get_registrations_by_interface(
            IUnregisteredService
        )
        assert registrations == []

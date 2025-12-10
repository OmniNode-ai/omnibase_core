"""Memory leak tests for ServiceRegistry - repeated registration/unregistration cycles."""

import gc
import sys
import weakref
from uuid import UUID

import pytest

from omnibase_core.container.service_registry import ServiceRegistry


# Test Protocol Interface
class ITestService:
    """Test service interface."""

    def execute(self) -> str:
        """Execute service logic."""
        return ""


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


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestServiceRegistryMemory:
    """Test suite for ServiceRegistry memory management.

    Note:
        Registry fixture is provided by conftest.py to avoid duplication.
    """

    @pytest.mark.asyncio
    async def test_registration_unregistration_cycle_no_leak(
        self, registry: ServiceRegistry
    ) -> None:
        """Test repeated registration/unregistration cycles don't leak memory."""
        # Get baseline internal state sizes
        initial_registrations = len(registry._registrations)
        initial_instances = len(registry._instances)
        initial_interface_map = len(registry._interface_map)
        initial_name_map = len(registry._name_map)

        # Perform 1000 registration/unregistration cycles
        cycles = 1000
        for i in range(cycles):
            # Register service
            service = MockServiceImplementation(f"test_{i}")
            registration_id = await registry.register_instance(
                interface=ITestService,
                instance=service,
                scope="global",
            )

            # Unregister immediately
            result = await registry.unregister_service(registration_id)
            assert result is True

        # Force garbage collection
        gc.collect()

        # Verify internal state returned to baseline
        assert len(registry._registrations) == initial_registrations
        assert len(registry._instances) == initial_instances
        assert len(registry._interface_map) == initial_interface_map
        assert len(registry._name_map) == initial_name_map

    @pytest.mark.asyncio
    async def test_interface_map_cleanup(self, registry: ServiceRegistry) -> None:
        """Test interface_map entry removed after unregistration."""
        # Verify interface_map starts empty (or at baseline)
        initial_interface_count = len(registry._interface_map)

        # Register service
        service = MockServiceImplementation("test")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Verify interface_map has entry
        assert "ITestService" in registry._interface_map
        assert registration_id in registry._interface_map["ITestService"]

        # Unregister service
        await registry.unregister_service(registration_id)

        # Verify interface_map cleaned up
        # If this was the last registration for ITestService, the entry should be removed
        if "ITestService" in registry._interface_map:
            assert registration_id not in registry._interface_map["ITestService"]
        # Otherwise, the entire key should be gone
        else:
            assert len(registry._interface_map) == initial_interface_count

    @pytest.mark.asyncio
    async def test_name_map_cleanup(self, registry: ServiceRegistry) -> None:
        """Test name_map entry removed after unregistration."""
        # Get baseline
        initial_name_count = len(registry._name_map)

        # Register service
        service = MockServiceImplementation("test")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Verify name_map has entry
        assert "MockServiceImplementation" in registry._name_map
        assert registry._name_map["MockServiceImplementation"] == registration_id

        # Unregister service
        await registry.unregister_service(registration_id)

        # Verify name_map entry removed
        assert "MockServiceImplementation" not in registry._name_map
        assert len(registry._name_map) == initial_name_count

    @pytest.mark.asyncio
    async def test_instance_disposal_releases_references(
        self, registry: ServiceRegistry
    ) -> None:
        """Test instance disposal properly releases references."""
        # Create service with weak reference tracking
        service = MockServiceImplementation("test")
        weak_ref = weakref.ref(service)

        # Verify object exists
        assert weak_ref() is not None

        # Register instance
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Clear local reference (registry still holds reference)
        del service

        # Verify registry still holds reference
        instances = await registry.get_active_instances(registration_id)
        assert len(instances) == 1
        assert weak_ref() is not None

        # Unregister service (should dispose instance)
        await registry.unregister_service(registration_id)

        # Force garbage collection
        gc.collect()

        # Verify object was collected
        assert weak_ref() is None

    @pytest.mark.asyncio
    async def test_repeated_resolve_no_accumulation(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolving same service doesn't create new instances (singleton)."""
        # Register singleton service
        service = MockServiceImplementation("singleton")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Get baseline instance count
        initial_instances = await registry.get_active_instances(registration_id)
        assert len(initial_instances) == 1

        # Resolve service 100 times
        for _ in range(100):
            resolved = await registry.resolve_service(ITestService)
            assert resolved is service

        # Verify instance count didn't increase
        final_instances = await registry.get_active_instances(registration_id)
        assert len(final_instances) == len(initial_instances)

        # Verify only one instance exists
        assert len(final_instances) == 1

    @pytest.mark.asyncio
    async def test_registry_internal_state_consistency(
        self, registry: ServiceRegistry
    ) -> None:
        """Test internal data structures stay consistent during lifecycle."""
        # Track multiple registrations
        registration_ids: list[UUID] = []

        # Register 10 services
        for i in range(10):
            service = MockServiceImplementation(f"test_{i}")
            reg_id = await registry.register_instance(
                interface=ITestService,
                instance=service,
                scope="global",
            )
            registration_ids.append(reg_id)

        # Verify consistency
        assert len(registry._registrations) >= 10
        assert len(registry._instances) >= 10

        # Verify all registrations are in interface_map
        assert "ITestService" in registry._interface_map
        for reg_id in registration_ids:
            assert reg_id in registry._interface_map["ITestService"]

        # Unregister half of them
        for reg_id in registration_ids[:5]:
            await registry.unregister_service(reg_id)

        # Verify consistency after partial cleanup
        for reg_id in registration_ids[:5]:
            # Should be removed from registrations
            assert reg_id not in registry._registrations
            # Should be removed from instances
            assert reg_id not in registry._instances
            # Should be removed from interface_map
            assert reg_id not in registry._interface_map["ITestService"]

        # Verify remaining registrations are still valid
        for reg_id in registration_ids[5:]:
            assert reg_id in registry._registrations
            assert reg_id in registry._instances
            assert reg_id in registry._interface_map["ITestService"]

    @pytest.mark.asyncio
    async def test_gc_collects_unregistered_services(
        self, registry: ServiceRegistry
    ) -> None:
        """Test garbage collection works properly after unregistration."""
        # Create multiple services with weak references
        weak_refs: list[weakref.ref] = []
        registration_ids: list[UUID] = []

        for i in range(10):
            service = MockServiceImplementation(f"test_{i}")
            weak_ref = weakref.ref(service)
            weak_refs.append(weak_ref)

            reg_id = await registry.register_instance(
                interface=ITestService,
                instance=service,
                scope="global",
            )
            registration_ids.append(reg_id)

            # Clear local reference
            del service

        # Verify all services still alive (held by registry)
        gc.collect()
        alive_count = sum(1 for ref in weak_refs if ref() is not None)
        assert alive_count == 10

        # Unregister all services
        for reg_id in registration_ids:
            await registry.unregister_service(reg_id)

        # Force garbage collection
        gc.collect()

        # Verify all services were collected
        alive_count = sum(1 for ref in weak_refs if ref() is not None)
        assert alive_count == 0

    @pytest.mark.asyncio
    async def test_multiple_interface_registrations_cleanup(
        self, registry: ServiceRegistry
    ) -> None:
        """Test cleanup when multiple services share same interface."""
        # Register 5 services for same interface
        registration_ids: list[UUID] = []

        for i in range(5):
            service = MockServiceImplementation(f"test_{i}")
            reg_id = await registry.register_instance(
                interface=ITestService,
                instance=service,
                scope="global",
            )
            registration_ids.append(reg_id)

        # Verify all in interface_map
        assert "ITestService" in registry._interface_map
        assert len(registry._interface_map["ITestService"]) >= 5

        # Unregister first 3
        for reg_id in registration_ids[:3]:
            await registry.unregister_service(reg_id)

        # Verify partial cleanup - interface_map should still exist
        assert "ITestService" in registry._interface_map
        for reg_id in registration_ids[:3]:
            assert reg_id not in registry._interface_map["ITestService"]

        # Verify remaining 2 still exist
        for reg_id in registration_ids[3:]:
            assert reg_id in registry._interface_map["ITestService"]

        # Unregister remaining 2
        for reg_id in registration_ids[3:]:
            await registry.unregister_service(reg_id)

        # Verify complete cleanup - interface_map entry should be removed
        # (unless other tests have added ITestService registrations)
        if "ITestService" in registry._interface_map:
            assert len(registry._interface_map["ITestService"]) == 0

    @pytest.mark.asyncio
    async def test_instance_reference_count(self, registry: ServiceRegistry) -> None:
        """Test reference counts during lifecycle operations."""
        # Create service
        service = MockServiceImplementation("test")

        # Get reference count before registration (includes local var + function args)
        # Note: sys.getrefcount adds 1 for the temporary reference it creates
        refcount_before = sys.getrefcount(service)

        # Register instance
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Reference count should increase (registry holds reference)
        refcount_after_register = sys.getrefcount(service)
        assert refcount_after_register > refcount_before

        # Resolve service (should return same instance, not increase refcount permanently)
        resolved = await registry.resolve_service(ITestService)
        assert resolved is service

        # Clear resolved reference
        del resolved

        # Unregister (should release registry's reference)
        await registry.unregister_service(registration_id)

        # Force garbage collection
        gc.collect()

        # Reference count should return to baseline or lower
        # (only local 'service' variable remains)
        refcount_after_unregister = sys.getrefcount(service)
        assert refcount_after_unregister < refcount_after_register

    @pytest.mark.asyncio
    async def test_dispose_instances_releases_memory(
        self, registry: ServiceRegistry
    ) -> None:
        """Test dispose_instances properly releases memory."""
        # Register service
        service = MockServiceImplementation("test")
        weak_ref = weakref.ref(service)

        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
        )

        # Clear local reference
        del service

        # Verify registry holds reference
        assert weak_ref() is not None

        # Dispose instances (but don't unregister)
        disposed_count = await registry.dispose_instances(registration_id)
        assert disposed_count == 1

        # Force garbage collection
        gc.collect()

        # Verify instance was collected (ModelServiceInstance.dispose sets instance to None)
        assert weak_ref() is None

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.timeout(120)
    async def test_stress_test_memory_stability(
        self, registry: ServiceRegistry
    ) -> None:
        """Stress test: rapid register/unregister cycles with multiple services.

        Note:
        - Marked as @slow due to 1000 iterations of register/unregister cycles
        - Extended timeout (120s) for CI environments
        """
        # Baseline
        initial_registrations = len(registry._registrations)
        initial_instances = len(registry._instances)

        # Stress test: 100 iterations of 10 services each
        for iteration in range(100):
            registration_ids: list[UUID] = []

            # Register 10 services
            for i in range(10):
                service = MockServiceImplementation(f"stress_{iteration}_{i}")
                reg_id = await registry.register_instance(
                    interface=ITestService,
                    instance=service,
                    scope="global",
                )
                registration_ids.append(reg_id)

            # Unregister all
            for reg_id in registration_ids:
                await registry.unregister_service(reg_id)

            # Periodic GC
            if iteration % 10 == 0:
                gc.collect()

        # Final GC
        gc.collect()

        # Verify no memory accumulation
        assert len(registry._registrations) == initial_registrations
        assert len(registry._instances) == initial_instances

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_service(
        self, registry: ServiceRegistry
    ) -> None:
        """Test unregistering non-existent service doesn't cause memory issues."""
        from uuid import uuid4

        # Get baseline
        initial_registrations = len(registry._registrations)

        # Try to unregister non-existent service
        fake_id = uuid4()
        result = await registry.unregister_service(fake_id)

        # Should return False
        assert result is False

        # Should not affect internal state
        assert len(registry._registrations) == initial_registrations

        # No memory leaks
        gc.collect()

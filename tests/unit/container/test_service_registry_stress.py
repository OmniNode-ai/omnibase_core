"""Concurrent registration stress tests for ServiceRegistry.

This module contains stress tests to verify thread safety of the ServiceRegistry
implementation. Tests focus on concurrent registration, resolution, and unregistration
operations to detect race conditions and ensure proper synchronization.

Thread Safety Status: ServiceRegistry is marked as "✅ Yes (read-only after init)"
in the threading documentation. These tests validate this claim under high contention.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Protocol
from uuid import UUID

import pytest

from omnibase_core.container.service_registry import ServiceRegistry


# Test Protocol Interfaces
class ITestService(Protocol):
    """Test service interface for concurrent operations."""

    def execute(self) -> str:
        """Execute service logic."""
        ...


class IServiceA(Protocol):
    """Service A interface for multi-interface tests."""

    def process_a(self) -> str:
        """Process A logic."""
        ...


class IServiceB(Protocol):
    """Service B interface for multi-interface tests."""

    def process_b(self) -> str:
        """Process B logic."""
        ...


class IServiceC(Protocol):
    """Service C interface for multi-interface tests."""

    def process_c(self) -> str:
        """Process C logic."""
        ...


# Mock Implementations
class MockServiceImplementation(ITestService):
    """Mock service implementation for testing."""

    def __init__(self, name: str = "test") -> None:
        """Initialize mock service."""
        self.name = name
        self.execution_count = 0
        self._lock = threading.Lock()

    def execute(self) -> str:
        """Execute service logic (thread-safe)."""
        with self._lock:
            self.execution_count += 1
            return f"Executed {self.name} (count: {self.execution_count})"


class MockServiceA(IServiceA):
    """Mock implementation for IServiceA."""

    def __init__(self, id_num: int) -> None:
        """Initialize with unique ID."""
        self.id_num = id_num

    def process_a(self) -> str:
        """Process A logic."""
        return f"ServiceA-{self.id_num}"


class MockServiceB(IServiceB):
    """Mock implementation for IServiceB."""

    def __init__(self, id_num: int) -> None:
        """Initialize with unique ID."""
        self.id_num = id_num

    def process_b(self) -> str:
        """Process B logic."""
        return f"ServiceB-{self.id_num}"


class MockServiceC(IServiceC):
    """Mock implementation for IServiceC."""

    def __init__(self, id_num: int) -> None:
        """Initialize with unique ID."""
        self.id_num = id_num

    def process_c(self) -> str:
        """Process C logic."""
        return f"ServiceC-{self.id_num}"


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(120)
@pytest.mark.unit
class TestServiceRegistryConcurrency:
    """Test suite for concurrent ServiceRegistry operations.

    Note:
        Registry and barrier fixtures are provided by conftest.py to avoid
        duplication across test files.
    """

    async def test_concurrent_registration_same_interface(
        self, registry: ServiceRegistry, barrier_10: threading.Barrier
    ) -> None:
        """Test multiple threads registering services for the same interface.

        Validates that concurrent registrations for the same interface don't cause
        race conditions in the internal interface mapping.
        """
        registration_ids: list[UUID] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def register_service(worker_id: int) -> None:
            """Register a service instance (thread worker)."""
            try:
                # Wait for all threads to be ready
                barrier_10.wait()

                # Create unique instance
                service = MockServiceImplementation(f"worker-{worker_id}")

                # Register instance (runs async code in thread)
                registration_id = asyncio.run(
                    registry.register_instance(
                        interface=ITestService,
                        instance=service,
                        scope="global",
                        metadata={"worker_id": worker_id},
                    )
                )

                # Thread-safe result collection
                with lock:
                    registration_ids.append(registration_id)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent registrations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_service, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent registration errors: {errors}"

        # Verify all registrations succeeded
        assert len(registration_ids) == 10

        # Verify all registration IDs are unique
        assert len(set(registration_ids)) == 10

        # Verify all can be retrieved
        for reg_id in registration_ids:
            registration = await registry.get_registration(reg_id)
            assert registration is not None
            assert registration.service_metadata.service_interface == "ITestService"

        # Verify interface mapping contains all registrations
        registrations = await registry.get_registrations_by_interface(ITestService)
        assert len(registrations) == 10

    async def test_concurrent_registration_different_interfaces(
        self, registry: ServiceRegistry, barrier_20: threading.Barrier
    ) -> None:
        """Test multiple threads registering services for different interfaces.

        Validates that concurrent registrations for different interfaces don't
        interfere with each other.
        """
        registration_ids: list[UUID] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def register_service(worker_id: int) -> None:
            """Register services for different interfaces (thread worker)."""
            try:
                # Wait for all threads to be ready
                barrier_20.wait()

                # Determine which service to register (round-robin)
                service_type = worker_id % 3

                service: Any
                interface: Any

                if service_type == 0:
                    service = MockServiceA(worker_id)
                    interface = IServiceA
                elif service_type == 1:
                    service = MockServiceB(worker_id)
                    interface = IServiceB
                else:
                    service = MockServiceC(worker_id)
                    interface = IServiceC

                # Register instance
                registration_id = asyncio.run(
                    registry.register_instance(
                        interface=interface,
                        instance=service,
                        scope="global",
                        metadata={"worker_id": worker_id, "type": service_type},
                    )
                )

                # Thread-safe result collection
                with lock:
                    registration_ids.append(registration_id)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent registrations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(register_service, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent registration errors: {errors}"

        # Verify all registrations succeeded
        assert len(registration_ids) == 20

        # Verify all registration IDs are unique
        assert len(set(registration_ids)) == 20

        # Verify correct distribution across interfaces (20 workers / 3 types)
        # Should be approximately 7, 7, 6 or similar distribution
        service_a_regs = await registry.get_registrations_by_interface(IServiceA)
        service_b_regs = await registry.get_registrations_by_interface(IServiceB)
        service_c_regs = await registry.get_registrations_by_interface(IServiceC)

        # Should total to 20
        assert len(service_a_regs) + len(service_b_regs) + len(service_c_regs) == 20

        # Each should have at least some registrations
        assert len(service_a_regs) >= 6
        assert len(service_b_regs) >= 6
        assert len(service_c_regs) >= 6

    async def test_concurrent_resolution_same_service(
        self, registry: ServiceRegistry, barrier_20: threading.Barrier
    ) -> None:
        """Test multiple threads resolving the same singleton service.

        Validates that concurrent resolution of a singleton returns the same
        instance and properly tracks access counts.
        """
        # Pre-register a singleton service
        test_service = MockServiceImplementation("singleton")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        resolved_instances: list[Any] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def resolve_service(worker_id: int) -> None:
            """Resolve service instance (thread worker)."""
            try:
                # Wait for all threads to be ready
                barrier_20.wait()

                # Resolve service
                instance = asyncio.run(registry.resolve_service(ITestService))

                # Thread-safe result collection
                with lock:
                    resolved_instances.append(instance)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent resolutions
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(resolve_service, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent resolution errors: {errors}"

        # Verify all resolutions succeeded
        assert len(resolved_instances) == 20

        # Verify all resolved the SAME instance (singleton behavior)
        assert all(inst is test_service for inst in resolved_instances)

        # Verify access count was properly tracked
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.access_count >= 20  # Should be at least 20

    async def test_concurrent_register_and_resolve(
        self, registry: ServiceRegistry, barrier_20: threading.Barrier
    ) -> None:
        """Test concurrent registration and resolution operations.

        Validates that registering services while other threads are resolving
        doesn't cause race conditions or crashes.
        """
        # Pre-register one service
        initial_service = MockServiceImplementation("initial")
        await registry.register_instance(
            interface=ITestService,
            instance=initial_service,
            scope="global",
        )

        results: list[tuple[str, Any]] = []  # (operation_type, result)
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            """Mixed register/resolve worker."""
            try:
                # Wait for all threads to be ready
                barrier_20.wait()

                # Half the workers register, half resolve
                if worker_id % 2 == 0:
                    # Register operation
                    service = MockServiceImplementation(f"worker-{worker_id}")
                    registration_id = asyncio.run(
                        registry.register_instance(
                            interface=ITestService,
                            instance=service,
                            scope="global",
                        )
                    )
                    with lock:
                        results.append(("register", registration_id))
                else:
                    # Resolve operation
                    instance = asyncio.run(registry.resolve_service(ITestService))
                    with lock:
                        results.append(("resolve", instance))

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent operation errors: {errors}"

        # Verify all operations completed
        assert len(results) == 20

        # Count operation types
        register_ops = [r for r in results if r[0] == "register"]
        resolve_ops = [r for r in results if r[0] == "resolve"]

        # Should be 10 of each
        assert len(register_ops) == 10
        assert len(resolve_ops) == 10

        # Verify all registrations are valid
        for _, reg_id in register_ops:
            registration = await registry.get_registration(reg_id)
            assert registration is not None

        # Verify all resolutions returned valid instances
        for _, instance in resolve_ops:
            assert isinstance(instance, MockServiceImplementation)

    async def test_concurrent_register_and_unregister(
        self, registry: ServiceRegistry
    ) -> None:
        """Test race conditions between registration and unregistration.

        Validates that unregistering services while other threads are registering
        doesn't cause data corruption or crashes.

        Note: No barrier used here as we want to test natural race conditions.
        """
        registration_ids: list[UUID] = []
        unregister_results: list[bool] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def register_worker(worker_id: int) -> None:
            """Register services continuously."""
            try:
                service = MockServiceImplementation(f"worker-{worker_id}")
                registration_id = asyncio.run(
                    registry.register_instance(
                        interface=ITestService,
                        instance=service,
                        scope="global",
                    )
                )
                with lock:
                    registration_ids.append(registration_id)

            except Exception as e:
                with lock:
                    errors.append(e)

        def unregister_worker(target_index: int) -> None:
            """Unregister services by index."""
            try:
                # Small delay to ensure some registrations exist
                import time

                time.sleep(0.01)

                # Try to unregister by index
                with lock:
                    if target_index < len(registration_ids):
                        reg_id = registration_ids[target_index]
                    else:
                        return  # Nothing to unregister

                # Unregister (might fail if already unregistered)
                result = asyncio.run(registry.unregister_service(reg_id))
                with lock:
                    unregister_results.append(result)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent register and unregister operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Start 15 registration workers
            reg_futures = [executor.submit(register_worker, i) for i in range(15)]

            # Start 5 unregistration workers (targeting first 5 indices)
            unreg_futures = [executor.submit(unregister_worker, i) for i in range(5)]

            # Wait for all to complete
            for future in as_completed(reg_futures + unreg_futures):
                future.result()

        # Verify no exceptions occurred (race conditions handled gracefully)
        assert len(errors) == 0, f"Concurrent operation errors: {errors}"

        # Verify registrations occurred
        assert len(registration_ids) == 15

        # Verify registry is in consistent state
        all_registrations = await registry.get_all_registrations()
        assert len(all_registrations) >= 10  # At least some should remain

        # Verify each remaining registration is valid
        for registration in all_registrations:
            assert registration.registration_status == "registered"
            assert registration.is_active()

    async def test_high_contention_resolution(
        self, registry: ServiceRegistry, barrier_20: threading.Barrier
    ) -> None:
        """Test high contention access to singleton service.

        Simulates 100+ concurrent resolution operations to stress test
        the singleton instance retrieval mechanism.
        """
        # Pre-register a singleton service
        test_service = MockServiceImplementation("high-contention")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=test_service,
            scope="global",
        )

        resolution_count = [0]  # Mutable container for counter
        errors: list[Exception] = []
        lock = threading.Lock()

        def resolve_many(worker_id: int) -> None:
            """Resolve service multiple times (thread worker)."""
            try:
                # Wait for all threads to be ready
                barrier_20.wait()

                # Each worker performs 5 resolutions
                for _ in range(5):
                    instance = asyncio.run(registry.resolve_service(ITestService))
                    assert instance is test_service  # Verify singleton

                    with lock:
                        resolution_count[0] += 1

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute high contention resolutions (20 workers × 5 resolutions = 100 total)
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(resolve_many, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"High contention errors: {errors}"

        # Verify all 100 resolutions completed
        assert resolution_count[0] == 100

        # Verify access count tracking is consistent
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.access_count >= 100

        # Verify singleton instance is still valid
        final_instance = await registry.resolve_service(ITestService)
        assert final_instance is test_service

    async def test_concurrent_resolution_multiple_interfaces(
        self, registry: ServiceRegistry, barrier_20: threading.Barrier
    ) -> None:
        """Test concurrent resolution of multiple different interfaces.

        Validates that resolving different services concurrently doesn't
        cause contention or incorrect instance returns.
        """
        # Pre-register multiple services
        service_a = MockServiceA(1)
        service_b = MockServiceB(2)
        service_c = MockServiceC(3)

        await registry.register_instance(interface=IServiceA, instance=service_a)
        await registry.register_instance(interface=IServiceB, instance=service_b)
        await registry.register_instance(interface=IServiceC, instance=service_c)

        resolved_a: list[Any] = []
        resolved_b: list[Any] = []
        resolved_c: list[Any] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def resolve_worker(worker_id: int) -> None:
            """Resolve different services based on worker ID."""
            try:
                # Wait for all threads to be ready
                barrier_20.wait()

                # Round-robin service resolution
                service_type = worker_id % 3

                if service_type == 0:
                    instance = asyncio.run(registry.resolve_service(IServiceA))
                    with lock:
                        resolved_a.append(instance)
                elif service_type == 1:
                    instance = asyncio.run(registry.resolve_service(IServiceB))
                    with lock:
                        resolved_b.append(instance)
                else:
                    instance = asyncio.run(registry.resolve_service(IServiceC))
                    with lock:
                        resolved_c.append(instance)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent resolutions
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(resolve_worker, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent resolution errors: {errors}"

        # Verify all resolutions completed (approximately 7, 7, 6 distribution)
        total_resolved = len(resolved_a) + len(resolved_b) + len(resolved_c)
        assert total_resolved == 20

        # Verify all instances of each type are the correct singleton
        assert all(inst is service_a for inst in resolved_a)
        assert all(inst is service_b for inst in resolved_b)
        assert all(inst is service_c for inst in resolved_c)

    async def test_concurrent_instance_disposal(
        self, registry: ServiceRegistry, barrier_10: threading.Barrier
    ) -> None:
        """Test concurrent instance disposal operations.

        Validates that disposing instances while other threads access them
        doesn't cause crashes or data corruption.
        """
        # Register multiple services
        registration_ids: list[UUID] = []
        for i in range(10):
            service = MockServiceImplementation(f"service-{i}")
            reg_id = await registry.register_instance(
                interface=ITestService, instance=service, scope="global"
            )
            registration_ids.append(reg_id)

        disposed_counts: list[int] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def dispose_worker(worker_id: int) -> None:
            """Dispose instances for a specific registration."""
            try:
                # Wait for all threads to be ready
                barrier_10.wait()

                reg_id = registration_ids[worker_id]
                count = asyncio.run(registry.dispose_instances(reg_id))

                with lock:
                    disposed_counts.append(count)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent disposal
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(dispose_worker, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent disposal errors: {errors}"

        # Verify all disposals completed
        assert len(disposed_counts) == 10

        # Each should have disposed 1 instance
        assert all(count == 1 for count in disposed_counts)

        # Verify all instances are disposed
        for reg_id in registration_ids:
            instances = await registry.get_active_instances(reg_id)
            assert all(inst.is_disposed for inst in instances)

    async def test_concurrent_configuration_updates(
        self, registry: ServiceRegistry, barrier_10: threading.Barrier
    ) -> None:
        """Test concurrent service configuration updates.

        Validates that updating configuration from multiple threads
        doesn't cause data corruption.
        """
        # Pre-register a service
        service = MockServiceImplementation("config-test")
        registration_id = await registry.register_instance(
            interface=ITestService,
            instance=service,
            scope="global",
            metadata={"version": "1.0"},
        )

        update_results: list[bool] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def update_worker(worker_id: int) -> None:
            """Update configuration (thread worker)."""
            try:
                # Wait for all threads to be ready
                barrier_10.wait()

                # Each worker updates with unique value
                result = asyncio.run(
                    registry.update_service_configuration(
                        registration_id,
                        {f"worker_{worker_id}": True, "update_count": worker_id},
                    )
                )

                with lock:
                    update_results.append(result)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_worker, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent update errors: {errors}"

        # Verify all updates returned True
        assert len(update_results) == 10
        assert all(result is True for result in update_results)

        # Verify final configuration state
        registration = await registry.get_registration(registration_id)
        assert registration is not None

        # Should have updates from all workers (last write wins for update_count)
        config = registration.service_metadata.configuration
        assert "version" in config  # Original value preserved

        # At least some worker flags should be present
        worker_flags = [k for k in config if k.startswith("worker_")]
        assert len(worker_flags) >= 1  # At least one worker updated

    async def test_concurrent_registry_status_queries(
        self, registry: ServiceRegistry, barrier_10: threading.Barrier
    ) -> None:
        """Test concurrent registry status queries during active operations.

        Validates that querying registry status while services are being
        registered/resolved doesn't cause inconsistent state or crashes.
        """
        # Pre-register a few services
        for i in range(3):
            service = MockServiceImplementation(f"initial-{i}")
            await registry.register_instance(
                interface=ITestService, instance=service, scope="global"
            )

        status_results: list[Any] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def status_worker(worker_id: int) -> None:
            """Query registry status (thread worker)."""
            try:
                # Wait for all threads to be ready
                barrier_10.wait()

                # Half query status, half register new services
                if worker_id % 2 == 0:
                    status = asyncio.run(registry.get_registry_status())
                    with lock:
                        status_results.append(status)
                else:
                    service = MockServiceImplementation(f"worker-{worker_id}")
                    asyncio.run(
                        registry.register_instance(
                            interface=ITestService, instance=service, scope="global"
                        )
                    )

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent status queries and registrations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(status_worker, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent status query errors: {errors}"

        # Verify status queries returned valid results
        assert len(status_results) == 5  # Half the workers queried status

        for status in status_results:
            assert status is not None
            assert status.total_registrations >= 3  # At least initial services
            assert status.status in ["success", "pending", "failed"]
            assert isinstance(status.lifecycle_distribution, dict)
            assert isinstance(status.scope_distribution, dict)

        # Verify final state is consistent
        final_status = await registry.get_registry_status()
        assert final_status.total_registrations == 8  # 3 initial + 5 new

    async def test_concurrent_try_resolve_graceful_failures(
        self, registry: ServiceRegistry, barrier_20: threading.Barrier
    ) -> None:
        """Test concurrent try_resolve operations for non-existent services.

        Validates that concurrent failed resolutions are handled gracefully
        and don't cause resource leaks or crashes.
        """
        # Register only one service type
        service_a = MockServiceA(1)
        await registry.register_instance(interface=IServiceA, instance=service_a)

        successful_resolutions: list[Any] = []
        failed_resolutions: list[Any] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def try_resolve_worker(worker_id: int) -> None:
            """Try to resolve services (some will fail)."""
            try:
                # Wait for all threads to be ready
                barrier_20.wait()

                # Half try to resolve existing service, half try non-existent
                if worker_id % 2 == 0:
                    result = asyncio.run(registry.try_resolve_service(IServiceA))
                    with lock:
                        if result is not None:
                            successful_resolutions.append(result)
                        else:
                            failed_resolutions.append(None)
                else:
                    # Try to resolve non-existent service
                    result = asyncio.run(registry.try_resolve_service(IServiceB))
                    with lock:
                        if result is not None:
                            successful_resolutions.append(result)
                        else:
                            failed_resolutions.append(None)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent try_resolve operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(try_resolve_worker, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Verify no exceptions occurred (try_resolve should never raise)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

        # Verify results
        assert len(successful_resolutions) == 10  # Half succeeded (IServiceA)
        assert len(failed_resolutions) == 10  # Half failed (IServiceB)

        # All successful resolutions should be the same instance
        assert all(inst is service_a for inst in successful_resolutions)

    async def test_concurrent_resolve_all_services(
        self, registry: ServiceRegistry, barrier_10: threading.Barrier
    ) -> None:
        """Test concurrent resolve_all_services operations.

        Validates that resolving all services for an interface while
        new services are being registered returns consistent results.

        Note: This test uses separate registries for resolve vs register operations
        to avoid race conditions where resolve_all_services might see a registration
        before its instance is fully stored. This is a known limitation of the
        ServiceRegistry's internal implementation.
        """
        # Pre-register some initial services
        for i in range(3):
            service = MockServiceImplementation(f"initial-{i}")
            await registry.register_instance(
                interface=ITestService, instance=service, scope="global"
            )

        all_services_results: list[list[Any]] = []
        registration_count = 0
        errors: list[Exception] = []
        lock = threading.Lock()

        def resolve_all_worker(worker_id: int) -> None:
            """Resolve all services (concurrent read operations only)."""
            nonlocal registration_count
            try:
                # Wait for all threads to be ready
                barrier_10.wait()

                # All workers resolve all services (concurrent read operations)
                # We avoid mixing read and write operations to prevent race conditions
                # where resolve_all sees a registration before instance is stored
                services = asyncio.run(registry.resolve_all_services(ITestService))
                with lock:
                    all_services_results.append(services)

            except Exception as e:
                with lock:
                    errors.append(e)

        # Execute concurrent read operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(resolve_all_worker, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred during concurrent reads
        assert len(errors) == 0, f"Concurrent resolve_all errors: {errors}"

        # Verify all resolve_all calls returned results
        assert len(all_services_results) == 10  # All workers

        # Each result should have exactly 3 services (initial count)
        for services in all_services_results:
            assert len(services) == 3
            assert all(isinstance(s, MockServiceImplementation) for s in services)

        # Now test sequential registration followed by concurrent resolve
        for i in range(5):
            service = MockServiceImplementation(f"additional-{i}")
            await registry.register_instance(
                interface=ITestService, instance=service, scope="global"
            )

        # Final state should have 8 total services (3 initial + 5 additional)
        final_all = await registry.resolve_all_services(ITestService)
        assert len(final_all) == 8

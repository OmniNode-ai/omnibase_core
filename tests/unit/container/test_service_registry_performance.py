"""Performance tests for ServiceRegistry - large-scale handler/node registration.

This module tests ServiceRegistry scalability with 1000+ registered services,
measuring registration throughput, resolution latency, and memory usage patterns.
"""

import time
from typing import Any
from uuid import UUID

import pytest

from omnibase_core.container.service_registry import ServiceRegistry

# ===== Dynamic Interface and Implementation Factories =====


def create_test_interface(name: str) -> type:
    """Create a unique interface type for testing.

    Args:
        name: Unique interface name

    Returns:
        New interface type
    """
    return type(
        name,
        (),
        {
            "execute": lambda self: f"execute_{name}",
            "__module__": __name__,
        },
    )


def create_test_implementation(interface: type, name: str) -> Any:
    """Create a mock implementation instance.

    Args:
        interface: Interface type to implement
        name: Implementation name

    Returns:
        Mock implementation instance
    """

    def init_method(self: Any) -> None:
        """Initialize implementation."""
        self.name = name
        self.execution_count = 0

    def execute_method(self: Any) -> str:
        """Execute service logic."""
        self.execution_count += 1
        return f"Executed {self.name} (count: {self.execution_count})"

    # Create a new class that inherits from the interface dynamically
    ImplClass = type(
        f"{name}Implementation",
        (interface,),  # Inherit from interface
        {
            "__init__": init_method,
            "execute": execute_method,
            "__module__": __name__,
        },
    )

    return ImplClass()


# ===== Performance Test Suite =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestServiceRegistryPerformance:
    """Performance test suite for ServiceRegistry with large-scale registrations.

    Note:
        Registry fixture is provided by conftest.py to avoid duplication.
    """

    @pytest.mark.asyncio
    async def test_register_1000_services(self, registry: ServiceRegistry) -> None:
        """Test registering 1000 different service instances.

        Validates:
        - Registry can handle 1000+ registrations
        - Registration performance remains stable
        - All registrations are accessible

        Performance Threshold:
        - Average registration time < 1ms per service
        - Total registration time < 1 second

        Threshold Rationale:
            - 1ms/service allows for 1000 registrations/second
            - Registry operations: dict insertion (~O(1), ~1µs) + metadata (~10µs)
            - Interface map update: ~50-100µs per registration
            - Total overhead: ~100-200µs expected, 1ms threshold provides margin

            CI considerations:
            - GitHub Actions 2-core runners may show higher variance
            - Async operations may queue during high load
            - Threshold is 5x expected time for CI reliability

            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md
        """
        num_services = 1000
        registration_ids: list[UUID] = []
        start_time = time.perf_counter()

        # Register 1000 services
        for i in range(num_services):
            interface = create_test_interface(f"IService{i}")
            instance = create_test_implementation(interface, f"Service{i}")

            reg_id = await registry.register_instance(
                interface=interface,
                instance=instance,
                scope="global",
            )
            registration_ids.append(reg_id)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_service = (total_time / num_services) * 1000  # Convert to ms

        # Verify all registrations succeeded
        assert len(registration_ids) == num_services
        all_registrations = await registry.get_all_registrations()
        assert len(all_registrations) >= num_services

        # Verify performance thresholds
        assert avg_time_per_service < 1.0, (
            f"Average registration time {avg_time_per_service:.3f}ms exceeds 1ms threshold"
        )
        assert total_time < 1.0, (
            f"Total registration time {total_time:.3f}s exceeds 1s threshold"
        )

        print(
            f"\n✅ Registered {num_services} services in {total_time:.3f}s "
            f"(avg: {avg_time_per_service:.3f}ms per service)"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.timeout(120)
    async def test_register_5000_services(self, registry: ServiceRegistry) -> None:
        """Test registry scalability with 5000 services.

        Validates:
        - Registry can handle 5000+ registrations
        - Performance degrades gracefully (linear growth acceptable)
        - Memory usage remains manageable

        Performance Threshold:
        - Average registration time < 2ms per service
        - Total registration time < 10 seconds

        Note:
        - Marked as @slow due to 5000-service scale
        - Extended timeout (120s) for CI environments
        """
        num_services = 5000
        registration_ids: list[UUID] = []
        start_time = time.perf_counter()

        # Register 5000 services
        for i in range(num_services):
            interface = create_test_interface(f"ILargeScaleService{i}")
            instance = create_test_implementation(interface, f"LargeScaleService{i}")

            reg_id = await registry.register_instance(
                interface=interface,
                instance=instance,
                scope="global",
            )
            registration_ids.append(reg_id)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_service = (total_time / num_services) * 1000  # Convert to ms

        # Verify all registrations succeeded
        assert len(registration_ids) == num_services
        status = await registry.get_registry_status()
        assert status.total_registrations >= num_services

        # Verify performance thresholds (more lenient for larger scale)
        assert avg_time_per_service < 2.0, (
            f"Average registration time {avg_time_per_service:.3f}ms exceeds 2ms threshold"
        )
        assert total_time < 10.0, (
            f"Total registration time {total_time:.3f}s exceeds 10s threshold"
        )

        print(
            f"\n✅ Registered {num_services} services in {total_time:.3f}s "
            f"(avg: {avg_time_per_service:.3f}ms per service)"
        )

    @pytest.mark.asyncio
    async def test_resolution_latency_large_registry(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolution latency with 1000+ registered services.

        Validates:
        - Resolution time remains fast even with large registry
        - Interface map lookup is efficient
        - Performance does not degrade with registry size

        Performance Threshold:
        - Average resolution time < 0.5ms per service
        """
        num_services = 1000

        # Register 1000 services
        interfaces: list[type] = []
        for i in range(num_services):
            interface = create_test_interface(f"IResolutionTest{i}")
            instance = create_test_implementation(interface, f"ResolutionTest{i}")

            await registry.register_instance(
                interface=interface,
                instance=instance,
                scope="global",
            )
            interfaces.append(interface)

        # Measure resolution latency for random services
        resolution_times: list[float] = []
        num_resolutions = 100  # Test 100 resolutions

        for i in range(num_resolutions):
            # Pick a service to resolve (use modulo to cycle through)
            interface_to_resolve = interfaces[i % len(interfaces)]

            start_time = time.perf_counter()
            resolved = await registry.resolve_service(interface_to_resolve)
            end_time = time.perf_counter()

            resolution_time_ms = (end_time - start_time) * 1000
            resolution_times.append(resolution_time_ms)

            # Verify resolution succeeded
            assert resolved is not None

        # Calculate statistics
        avg_resolution_time = sum(resolution_times) / len(resolution_times)
        max_resolution_time = max(resolution_times)
        min_resolution_time = min(resolution_times)

        # Verify performance threshold
        assert avg_resolution_time < 0.5, (
            f"Average resolution time {avg_resolution_time:.3f}ms exceeds 0.5ms threshold"
        )

        print(
            f"\n✅ Resolution latency with {num_services} services: "
            f"avg={avg_resolution_time:.3f}ms, min={min_resolution_time:.3f}ms, "
            f"max={max_resolution_time:.3f}ms"
        )

    @pytest.mark.asyncio
    async def test_interface_lookup_with_many_implementations(
        self, registry: ServiceRegistry
    ) -> None:
        """Test interface map lookup with multiple implementations per interface.

        Validates:
        - Registry handles multiple implementations efficiently
        - resolve_all_services performs well
        - Interface map scales with implementations

        Performance Threshold:
        - resolve_all_services completes in < 100ms for 100 implementations
        """
        num_implementations = 100
        shared_interface = create_test_interface("ISharedService")

        # Register 100 implementations of same interface
        start_time = time.perf_counter()
        for i in range(num_implementations):
            instance = create_test_implementation(
                shared_interface, f"SharedImplementation{i}"
            )

            await registry.register_instance(
                interface=shared_interface,
                instance=instance,
                scope="global",
            )

        registration_time = time.perf_counter() - start_time

        # Resolve all implementations
        resolve_start = time.perf_counter()
        all_implementations = await registry.resolve_all_services(shared_interface)
        resolve_time = (time.perf_counter() - resolve_start) * 1000  # Convert to ms

        # Verify all implementations returned
        assert len(all_implementations) == num_implementations

        # Verify performance
        assert resolve_time < 100.0, (
            f"resolve_all_services took {resolve_time:.3f}ms, exceeds 100ms threshold"
        )

        print(
            f"\n✅ Registered {num_implementations} implementations in {registration_time:.3f}s, "
            f"resolved all in {resolve_time:.3f}ms"
        )

    @pytest.mark.asyncio
    async def test_registration_throughput(self, registry: ServiceRegistry) -> None:
        """Test registration throughput (operations per second).

        Validates:
        - Registry can handle rapid registration requests
        - Throughput meets minimum threshold

        Performance Threshold:
        - Throughput > 1000 registrations/second
        """
        num_services = 1000

        # Measure registration throughput
        start_time = time.perf_counter()

        for i in range(num_services):
            interface = create_test_interface(f"IThroughputTest{i}")
            instance = create_test_implementation(interface, f"ThroughputTest{i}")

            await registry.register_instance(
                interface=interface,
                instance=instance,
                scope="global",
            )

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate throughput
        throughput = num_services / total_time  # registrations per second

        # Verify throughput threshold
        assert throughput > 1000.0, (
            f"Throughput {throughput:.1f} ops/s is below 1000 ops/s threshold"
        )

        print(
            f"\n✅ Registration throughput: {throughput:.1f} registrations/second "
            f"({num_services} services in {total_time:.3f}s)"
        )

    @pytest.mark.asyncio
    async def test_get_all_registrations_performance(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_all_registrations performance with large registry.

        Validates:
        - Listing all registrations remains fast
        - No significant performance degradation with scale

        Performance Threshold:
        - List operation completes in < 10ms for 1000 registrations
        """
        num_services = 1000

        # Register 1000 services
        for i in range(num_services):
            interface = create_test_interface(f"IListTest{i}")
            instance = create_test_implementation(interface, f"ListTest{i}")

            await registry.register_instance(
                interface=interface,
                instance=instance,
                scope="global",
            )

        # Measure list operation performance
        start_time = time.perf_counter()
        all_registrations = await registry.get_all_registrations()
        list_time_ms = (time.perf_counter() - start_time) * 1000

        # Verify results
        assert len(all_registrations) >= num_services

        # Verify performance threshold
        assert list_time_ms < 10.0, (
            f"List operation took {list_time_ms:.3f}ms, exceeds 10ms threshold"
        )

        print(
            f"\n✅ Listed {len(all_registrations)} registrations in {list_time_ms:.3f}ms"
        )

    @pytest.mark.asyncio
    async def test_resolve_all_services_performance(
        self, registry: ServiceRegistry
    ) -> None:
        """Test resolve_all_services performance with many implementations.

        Validates:
        - Resolving all implementations scales efficiently
        - Instance retrieval remains fast

        Performance Threshold:
        - Resolve all completes in < 50ms for 100 implementations
        """
        num_implementations = 100
        shared_interface = create_test_interface("IResolveAllTest")

        # Register 100 implementations
        for i in range(num_implementations):
            instance = create_test_implementation(
                shared_interface, f"ResolveAllImpl{i}"
            )

            await registry.register_instance(
                interface=shared_interface,
                instance=instance,
                scope="global",
            )

        # Measure resolve_all performance
        start_time = time.perf_counter()
        all_services = await registry.resolve_all_services(shared_interface)
        resolve_time_ms = (time.perf_counter() - start_time) * 1000

        # Verify results
        assert len(all_services) == num_implementations

        # Verify performance threshold
        assert resolve_time_ms < 50.0, (
            f"resolve_all took {resolve_time_ms:.3f}ms, exceeds 50ms threshold"
        )

        print(
            f"\n✅ Resolved {num_implementations} implementations in {resolve_time_ms:.3f}ms"
        )

    @pytest.mark.asyncio
    async def test_registry_status_with_large_scale(
        self, registry: ServiceRegistry
    ) -> None:
        """Test get_registry_status performance and accuracy with large registry.

        Validates:
        - Status calculation remains efficient at scale
        - Distributions are calculated correctly
        - Metrics are accurate

        Performance Threshold:
        - Status calculation completes in < 100ms for 1000 registrations
        """
        num_services = 1000

        # Register 1000 services with varying scopes
        for i in range(num_services):
            interface = create_test_interface(f"IStatusTest{i}")
            instance = create_test_implementation(interface, f"StatusTest{i}")

            # Alternate between global and request scope
            scope = "global" if i % 2 == 0 else "request"

            await registry.register_instance(
                interface=interface,
                instance=instance,
                scope=scope,
            )

        # Measure status calculation performance
        start_time = time.perf_counter()
        status = await registry.get_registry_status()
        status_time_ms = (time.perf_counter() - start_time) * 1000

        # Verify status accuracy
        assert status.total_registrations >= num_services
        assert status.active_instances >= num_services
        assert status.is_healthy()

        # Verify distributions
        assert "singleton" in status.lifecycle_distribution
        assert "global" in status.scope_distribution
        assert "request" in status.scope_distribution

        # Verify performance threshold
        assert status_time_ms < 100.0, (
            f"Status calculation took {status_time_ms:.3f}ms, exceeds 100ms threshold"
        )

        print(
            f"\n✅ Calculated registry status for {num_services} services in {status_time_ms:.3f}ms"
        )
        print(f"   Lifecycle distribution: {status.lifecycle_distribution}")
        print(f"   Scope distribution: {status.scope_distribution}")


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestServiceRegistryMemoryUsage:
    """Memory usage tests for ServiceRegistry with large-scale registrations.

    Note:
        Registry fixture is provided by conftest.py to avoid duplication.
    """

    @pytest.mark.asyncio
    async def test_memory_pattern_with_1000_services(
        self, registry: ServiceRegistry
    ) -> None:
        """Test memory usage patterns with 1000 services.

        Validates:
        - Registry maintains reasonable memory footprint
        - No memory leaks in registration
        - Data structures scale efficiently

        Note: This is a basic validation test. Full memory profiling
        would require additional tooling (e.g., memory_profiler, tracemalloc).
        """
        num_services = 1000

        # Register 1000 services
        registration_ids: list[UUID] = []
        for i in range(num_services):
            interface = create_test_interface(f"IMemoryTest{i}")
            instance = create_test_implementation(interface, f"MemoryTest{i}")

            reg_id = await registry.register_instance(
                interface=interface,
                instance=instance,
                scope="global",
            )
            registration_ids.append(reg_id)

        # Verify all registrations exist
        status = await registry.get_registry_status()
        assert status.total_registrations >= num_services
        assert status.active_instances >= num_services

        # Verify internal data structures
        all_registrations = await registry.get_all_registrations()
        assert len(all_registrations) >= num_services

        # Verify cleanup works (helps validate no memory leaks)
        cleanup_count = 0
        for reg_id in registration_ids[:100]:  # Cleanup first 100
            result = await registry.unregister_service(reg_id)
            if result:
                cleanup_count += 1

        # Verify cleanup succeeded
        assert cleanup_count == 100

        # Verify registry state after cleanup
        status_after = await registry.get_registry_status()
        assert status_after.total_registrations == status.total_registrations - 100

        print(
            f"\n✅ Memory pattern test: Registered {num_services} services, "
            f"cleaned up {cleanup_count}, {status_after.total_registrations} remain"
        )

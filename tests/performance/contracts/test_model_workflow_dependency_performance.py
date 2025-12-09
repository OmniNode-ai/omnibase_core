"""
Performance Benchmarks for ModelWorkflowDependency Validation Operations.

Tests validation performance at scale to ensure ONEX compliance with large
dependency graphs and complex validation scenarios.

Strict typing is enforced: Performance must remain acceptable even with 1000+ dependencies.
"""

import time
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_workflow_dependency_type import EnumWorkflowDependencyType
from omnibase_core.models.contracts.model_workflow_condition import (
    EnumConditionOperator,
    EnumConditionType,
    ModelWorkflowCondition,
)
from omnibase_core.models.contracts.model_workflow_dependency import (
    ModelWorkflowDependency,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_condition_value import ModelConditionValue


class TestModelWorkflowDependencyPerformance:
    """Performance benchmarks for workflow dependency validation operations."""

    def _create_test_dependency(
        self,
        workflow_id: UUID | None = None,
        dependent_workflow_id: UUID | None = None,
        with_condition: bool = False,
        with_version: bool = False,
        dependency_type: EnumWorkflowDependencyType = EnumWorkflowDependencyType.SEQUENTIAL,
    ) -> ModelWorkflowDependency:
        """Create test dependency with optional components."""
        workflow_id = workflow_id or uuid4()
        dependent_workflow_id = dependent_workflow_id or uuid4()

        condition = None
        if with_condition:
            condition = ModelWorkflowCondition(
                condition_type=EnumConditionType.WORKFLOW_STATE,
                field_name="status",
                operator=EnumConditionOperator.EQUALS,
                expected_value=ModelConditionValue(value="completed"),
            )

        version = None
        if with_version:
            version = ModelSemVer(major=1, minor=0, patch=0)

        return ModelWorkflowDependency(
            workflow_id=workflow_id,
            dependent_workflow_id=dependent_workflow_id,
            dependency_type=dependency_type,
            condition=condition,
            version_constraint=version,
            required=True,
            timeout_ms=30000,
            description=f"Performance test dependency for {workflow_id}",
        )

    def test_single_dependency_validation_performance(self):
        """Test performance of single dependency validation."""
        # Warm up
        for _ in range(10):
            self._create_test_dependency()

        # Benchmark single validation
        start_time = time.perf_counter()
        iterations = 1000

        for _ in range(iterations):
            dependency = self._create_test_dependency(
                with_condition=True, with_version=True
            )
            # Validation happens automatically during instantiation
            assert dependency.workflow_id is not None

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_ms = (total_time / iterations) * 1000

        # Performance target: <1ms per dependency validation
        assert avg_time_ms < 1.0, (
            f"Single dependency validation too slow: {avg_time_ms:.2f}ms"
        )

        print(f"✅ Single dependency validation: {avg_time_ms:.3f}ms average")

    def test_circular_dependency_detection_performance(self):
        """Test performance of circular dependency detection at scale."""
        # Generate test UUIDs
        workflow_ids = [uuid4() for _ in range(100)]

        # Test non-circular dependencies (should be fast)
        start_time = time.perf_counter()

        for i in range(100):
            workflow_id = workflow_ids[i]
            dependent_id = workflow_ids[(i + 1) % 100]  # Next workflow in sequence

            dependency = self._create_test_dependency(
                workflow_id=workflow_id, dependent_workflow_id=dependent_id
            )
            assert dependency.workflow_id != dependency.dependent_workflow_id

        non_circular_time = time.perf_counter() - start_time

        # Test circular dependency detection (should still be fast)
        circular_detections = 0
        start_time = time.perf_counter()

        for workflow_id in workflow_ids[:50]:  # Test 50 circular attempts
            try:
                self._create_test_dependency(
                    workflow_id=workflow_id,
                    dependent_workflow_id=workflow_id,  # Same ID = circular
                )
            except ModelOnexError as e:
                if "CIRCULAR DEPENDENCY DETECTED" in str(e):
                    circular_detections += 1

        circular_detection_time = time.perf_counter() - start_time

        # Performance targets
        assert non_circular_time < 0.1, (
            f"Non-circular validation too slow: {non_circular_time:.3f}s"
        )
        assert circular_detection_time < 0.1, (
            f"Circular detection too slow: {circular_detection_time:.3f}s"
        )
        assert circular_detections == 50, (
            f"Expected 50 circular detections, got {circular_detections}"
        )

        print(
            f"✅ Non-circular validation (100 deps): {non_circular_time * 1000:.2f}ms"
        )
        print(
            f"✅ Circular detection (50 attempts): {circular_detection_time * 1000:.2f}ms"
        )

    def test_regex_pattern_performance(self):
        """Test performance of module path validation regex patterns."""
        # Test valid module paths (should be fast)
        valid_modules = [
            "omnibase.core.workflow",
            "omnibase_spi.protocols.event_bus",
            "service.module.submodule",
            "a.b.c.d.e.f.g.h.i.j",  # Deep nesting
            "very_long_module_name_with_underscores.another_very_long_name",
        ]

        # Test invalid module paths (should also be fast to reject)
        invalid_modules = [
            "module..double.dot",
            "module/with/slashes",
            "module\\with\\backslashes",
            "../path/traversal",
            "module<script>",
            "extremely_long_" + "module_" * 50 + "path",  # > 200 chars
        ]

        # Import to test regex performance directly
        from omnibase_core.models.contracts.model_dependency import ModelDependency

        # Benchmark valid module validation
        start_time = time.perf_counter()
        valid_count = 0

        for _ in range(200):  # Test each valid module 40 times
            for module in valid_modules:
                try:
                    dep = ModelDependency(name="TestDep", module=module)
                    assert dep.module == module
                    valid_count += 1
                except Exception:
                    pass  # Shouldn't happen for valid modules

        valid_time = time.perf_counter() - start_time

        # Benchmark invalid module rejection
        start_time = time.perf_counter()
        invalid_rejections = 0

        for _ in range(200):  # Test each invalid module 40 times
            for module in invalid_modules:
                try:
                    ModelDependency(name="TestDep", module=module)
                except (ModelOnexError, ValueError):
                    invalid_rejections += 1

        invalid_time = time.perf_counter() - start_time

        # Performance targets
        valid_avg_ms = (valid_time / valid_count) * 1000
        invalid_avg_ms = (invalid_time / len(invalid_modules) / 200) * 1000

        assert valid_avg_ms < 0.5, (
            f"Valid module validation too slow: {valid_avg_ms:.3f}ms"
        )
        assert invalid_avg_ms < 0.5, (
            f"Invalid module rejection too slow: {invalid_avg_ms:.3f}ms"
        )
        assert valid_count == 1000, (
            f"Expected 1000 valid validations, got {valid_count}"
        )
        assert invalid_rejections > 800, (
            f"Expected >800 rejections, got {invalid_rejections}"
        )

        print(f"✅ Valid module validation: {valid_avg_ms:.3f}ms average")
        print(f"✅ Invalid module rejection: {invalid_avg_ms:.3f}ms average")

    def test_large_dependency_graph_performance(self):
        """Test performance with large dependency graphs (1000+ dependencies)."""
        # Create a large set of dependencies
        num_dependencies = 1000
        workflow_ids = [uuid4() for _ in range(num_dependencies + 1)]

        dependencies: list[ModelWorkflowDependency] = []

        # Benchmark creating large dependency graph
        start_time = time.perf_counter()

        for i in range(num_dependencies):
            # Create chain: workflow[0] -> workflow[1] -> ... -> workflow[n]
            workflow_id = workflow_ids[i]
            dependent_id = workflow_ids[i + 1]

            # Add variety: some with conditions, versions, different types
            has_condition = i % 3 == 0
            has_version = i % 5 == 0
            dep_type = [
                EnumWorkflowDependencyType.SEQUENTIAL,
                EnumWorkflowDependencyType.PARALLEL,
                EnumWorkflowDependencyType.CONDITIONAL,
                EnumWorkflowDependencyType.BLOCKING,
            ][i % 4]

            dependency = self._create_test_dependency(
                workflow_id=workflow_id,
                dependent_workflow_id=dependent_id,
                with_condition=has_condition,
                with_version=has_version,
                dependency_type=dep_type,
            )
            dependencies.append(dependency)

        creation_time = time.perf_counter() - start_time

        # Benchmark dependency graph analysis
        start_time = time.perf_counter()

        # Analyze dependency characteristics
        sequential_count = sum(1 for d in dependencies if d.is_sequential())
        parallel_count = sum(1 for d in dependencies if d.is_parallel())
        conditional_count = sum(1 for d in dependencies if d.is_conditional())
        blocking_count = sum(1 for d in dependencies if d.is_blocking())
        required_count = sum(1 for d in dependencies if d.required)
        with_timeout_count = sum(1 for d in dependencies if d.timeout_ms is not None)

        analysis_time = time.perf_counter() - start_time

        # Performance targets
        assert creation_time < 2.0, (
            f"Large graph creation too slow: {creation_time:.2f}s"
        )
        assert analysis_time < 0.1, (
            f"Large graph analysis too slow: {analysis_time:.2f}s"
        )

        # Verify correctness
        assert len(dependencies) == num_dependencies
        assert (
            sequential_count + parallel_count + conditional_count + blocking_count
            == num_dependencies
        )
        assert required_count == num_dependencies  # All created as required
        assert with_timeout_count == num_dependencies  # All have timeout

        print(
            f"✅ Large graph creation ({num_dependencies} deps): {creation_time:.2f}s"
        )
        print(f"✅ Large graph analysis: {analysis_time * 1000:.2f}ms")
        print(
            f"📊 Graph stats: {sequential_count} seq, {parallel_count} par, {conditional_count} cond, {blocking_count} block"
        )

    def test_timeout_validation_performance(self):
        """Test performance of timeout validation with edge cases."""
        # Test valid timeout values
        valid_timeouts = [1, 1000, 30000, 60000, 300000]  # 1ms to 5min
        invalid_timeouts = [0, -1, 300001, 999999]  # Invalid values

        # Benchmark valid timeout validation
        start_time = time.perf_counter()
        valid_count = 0

        for _ in range(200):
            for timeout in valid_timeouts:
                try:
                    dep = self._create_test_dependency()
                    dep.timeout_ms = timeout
                    # Create new instance to trigger validation
                    new_dep = ModelWorkflowDependency(
                        workflow_id=dep.workflow_id,
                        dependent_workflow_id=dep.dependent_workflow_id,
                        dependency_type=dep.dependency_type,
                        timeout_ms=timeout,
                    )
                    assert new_dep.timeout_ms == timeout
                    valid_count += 1
                except Exception:
                    pass

        valid_time = time.perf_counter() - start_time

        # Benchmark invalid timeout rejection
        start_time = time.perf_counter()
        invalid_rejections = 0

        for _ in range(100):
            for timeout in invalid_timeouts:
                try:
                    ModelWorkflowDependency(
                        workflow_id=uuid4(),
                        dependent_workflow_id=uuid4(),
                        dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
                        timeout_ms=timeout,
                    )
                except (ModelOnexError, ValueError):
                    invalid_rejections += 1

        invalid_time = time.perf_counter() - start_time

        # Performance targets
        valid_avg_ms = (valid_time / valid_count) * 1000 if valid_count > 0 else 0
        invalid_avg_ms = (invalid_time / (len(invalid_timeouts) * 100)) * 1000

        assert valid_avg_ms < 1.0, f"Timeout validation too slow: {valid_avg_ms:.3f}ms"
        assert invalid_avg_ms < 1.0, (
            f"Invalid timeout rejection too slow: {invalid_avg_ms:.3f}ms"
        )
        assert invalid_rejections >= 300, (
            f"Expected ≥300 timeout rejections, got {invalid_rejections}"
        )

        print(f"✅ Timeout validation: {valid_avg_ms:.3f}ms average")
        print(f"✅ Invalid timeout rejection: {invalid_avg_ms:.3f}ms average")

    @pytest.mark.slow
    def test_memory_usage_large_graph(self):
        """Test memory efficiency with large dependency graphs."""
        import tracemalloc

        # Start memory tracing
        tracemalloc.start()

        # Create large dependency graph
        num_dependencies = 5000
        dependencies = []

        # Take initial memory snapshot
        snapshot1 = tracemalloc.take_snapshot()

        # Create dependencies
        for i in range(num_dependencies):
            dependency = self._create_test_dependency(
                with_condition=(i % 10 == 0),  # 10% with conditions
                with_version=(i % 20 == 0),  # 5% with versions
            )
            dependencies.append(dependency)

        # Take final memory snapshot
        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory usage
        top_stats = snapshot2.compare_to(snapshot1, "lineno")
        total_memory_kb = sum(stat.size for stat in top_stats) / 1024

        # Memory efficiency targets (realistic for complex objects with UUIDs, conditions, versions)
        memory_per_dep_bytes = (total_memory_kb * 1024) / num_dependencies
        assert memory_per_dep_bytes < 3000, (
            f"Memory usage too high: {memory_per_dep_bytes:.1f} bytes/dep"
        )
        assert total_memory_kb < 15000, (
            f"Total memory usage too high: {total_memory_kb:.1f} KB"
        )

        print(f"✅ Memory usage: {memory_per_dep_bytes:.1f} bytes per dependency")
        print(
            f"✅ Total memory: {total_memory_kb:.1f} KB for {num_dependencies} dependencies"
        )

        # Cleanup
        tracemalloc.stop()

    def test_concurrent_validation_simulation(self):
        """Simulate concurrent validation scenarios."""
        import queue
        import threading

        num_threads = 10
        deps_per_thread = 100
        results = queue.Queue()

        def validate_dependencies(thread_id: int):
            """Validate dependencies in a thread."""
            thread_results = []
            start_time = time.perf_counter()

            for i in range(deps_per_thread):
                try:
                    dependency = self._create_test_dependency(
                        with_condition=(i % 5 == 0),
                        with_version=(i % 3 == 0),
                    )
                    thread_results.append(True)
                except Exception:
                    thread_results.append(False)

            end_time = time.perf_counter()
            results.put((thread_id, len(thread_results), end_time - start_time))

        # Start all threads
        threads = []
        overall_start = time.perf_counter()

        for i in range(num_threads):
            thread = threading.Thread(target=validate_dependencies, args=(i,))
            thread.start()
            threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join()

        overall_end = time.perf_counter()
        overall_time = overall_end - overall_start

        # Collect results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())

        # Analyze concurrent performance
        total_validations = sum(count for _, count, _ in thread_results)
        max_thread_time = max(time for _, _, time in thread_results)
        avg_thread_time = sum(time for _, _, time in thread_results) / len(
            thread_results
        )

        # Performance targets
        assert overall_time < 5.0, (
            f"Concurrent validation too slow: {overall_time:.2f}s"
        )
        assert max_thread_time < 2.0, f"Slowest thread too slow: {max_thread_time:.2f}s"
        assert total_validations == num_threads * deps_per_thread

        throughput = total_validations / overall_time
        assert throughput > 200, f"Throughput too low: {throughput:.1f} validations/sec"

        print(f"✅ Concurrent validation: {throughput:.1f} deps/sec throughput")
        print(
            f"✅ Overall time: {overall_time:.2f}s, max thread: {max_thread_time:.2f}s"
        )
        print(
            f"✅ {num_threads} threads x {deps_per_thread} deps = {total_validations} validations"
        )


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([__file__, "-v", "-s"])

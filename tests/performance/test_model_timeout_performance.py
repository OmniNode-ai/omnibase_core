#!/usr/bin/env python3
"""
Performance tests for ModelTimeout optimizations.

These tests verify that the performance optimizations implemented based on
PR review comments actually provide measurable performance improvements.
"""

import time
from statistics import mean

import pytest

from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.models.infrastructure.model_timeout import ModelTimeout


class TestModelTimeoutPerformance:
    """Performance tests for ModelTimeout operations."""

    def time_operation(self, func, iterations: int = 100) -> float:
        """Time an operation over multiple iterations."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)
        return mean(times)

    def test_cached_property_performance(self):
        """Test that cached properties provide performance improvements."""
        timeout = ModelTimeout(
            timeout_seconds=30,
            warning_threshold_seconds=10,
            extension_limit_seconds=60,
            allow_extension=True,
            custom_metadata={"key1": "value1", "key2": 42},
        )

        # Test custom_properties caching
        def access_custom_properties():
            return timeout.custom_properties

        # First access (cache miss)
        first_access_time = self.time_operation(access_custom_properties, 1)

        # Subsequent accesses (cache hits)
        cached_access_time = self.time_operation(access_custom_properties, 10)

        # Cached access should be significantly faster
        # Allow some variance but expect at least 2x improvement
        assert cached_access_time < first_access_time * 0.5, (
            f"Cached access ({cached_access_time:.6f}s) should be much faster "
            f"than first access ({first_access_time:.6f}s)"
        )

    def test_warning_threshold_caching(self):
        """Test that warning_threshold_seconds caching improves performance."""
        timeout = ModelTimeout(timeout_seconds=60, warning_threshold_seconds=10)

        # Test warning threshold access
        def access_warning_threshold():
            return timeout.warning_threshold_seconds

        # Time multiple accesses
        access_time = self.time_operation(access_warning_threshold, 100)

        # Should be very fast due to caching (< 1ms average)
        assert (
            access_time < 0.001
        ), f"Warning threshold access ({access_time:.6f}s) should be very fast due to caching"

    def test_extension_limit_caching(self):
        """Test that extension_limit_seconds caching improves performance."""
        timeout = ModelTimeout(
            timeout_seconds=60,
            extension_limit_seconds=30,
            allow_extension=True,
        )

        # Test extension limit access
        def access_extension_limit():
            return timeout.extension_limit_seconds

        # Time multiple accesses
        access_time = self.time_operation(access_extension_limit, 100)

        # Should be very fast due to caching (< 1ms average)
        assert (
            access_time < 0.001
        ), f"Extension limit access ({access_time:.6f}s) should be very fast due to caching"

    def test_runtime_category_calculation_caching(self):
        """Test that runtime category calculations are cached effectively."""

        # Test the cached class method
        def create_from_category():
            return ModelTimeout.from_runtime_category(
                EnumRuntimeCategory.MODERATE,
                use_max_estimate=True,
            )

        # Time the operation
        creation_time = self.time_operation(create_from_category, 10)

        # Should be fast due to LRU caching
        assert (
            creation_time < 0.01
        ), f"Runtime category calculation ({creation_time:.6f}s) should be fast due to LRU caching"

    def test_cache_invalidation_on_metadata_change(self):
        """Test that cache is properly invalidated when metadata changes."""
        timeout = ModelTimeout(timeout_seconds=30, custom_metadata={"initial": "value"})

        # Access cached property
        initial_properties = timeout.custom_properties

        # Modify metadata (should invalidate cache)
        timeout.set_custom_metadata("new_key", "new_value")

        # Access again (should reflect changes)
        updated_properties = timeout.custom_properties

        # Verify cache was invalidated and new value is present
        assert "new_key" in updated_properties.model_dump().get("custom_strings", {})
        assert initial_properties != updated_properties

    def test_serialization_performance(self):
        """Test serialization/deserialization performance."""
        # Create timeout with various data
        timeout = ModelTimeout(
            timeout_seconds=30,
            warning_threshold_seconds=10,
            extension_limit_seconds=60,
            allow_extension=True,
            runtime_category=EnumRuntimeCategory.MODERATE,
            description="Test timeout",
            custom_metadata={"string_val": "test", "numeric_val": 42, "bool_val": True},
        )

        # Test serialization to typed data
        def serialize():
            return timeout.to_typed_data()

        serialize_time = self.time_operation(serialize, 50)

        # Test deserialization from typed data
        typed_data = timeout.to_typed_data()

        def deserialize():
            return ModelTimeout.model_validate_typed(typed_data)

        deserialize_time = self.time_operation(deserialize, 50)

        # Both operations should be reasonably fast
        assert (
            serialize_time < 0.01
        ), f"Serialization ({serialize_time:.6f}s) should be fast"
        assert (
            deserialize_time < 0.01
        ), f"Deserialization ({deserialize_time:.6f}s) should be fast"

    @pytest.mark.parametrize(
        "category",
        [
            EnumRuntimeCategory.FAST,
            EnumRuntimeCategory.MODERATE,
            # Add other categories as available
        ],
    )
    def test_lru_cache_effectiveness(self, category):
        """Test that LRU cache is effective for different runtime categories."""

        # Clear any existing cache
        ModelTimeout._calculate_timeout_from_category.cache_clear()

        # Time first call (cache miss)
        def first_call():
            return ModelTimeout._calculate_timeout_from_category(category, True)

        first_time = self.time_operation(first_call, 1)

        # Time subsequent calls (cache hits)
        def cached_call():
            return ModelTimeout._calculate_timeout_from_category(category, True)

        cached_time = self.time_operation(cached_call, 10)

        # Cached calls should be faster
        assert (
            cached_time < first_time
        ), f"Cached call ({cached_time:.6f}s) should be faster than first call ({first_time:.6f}s)"

    def test_property_access_patterns(self):
        """Test common property access patterns for performance."""
        timeout = ModelTimeout(
            timeout_seconds=30,
            warning_threshold_seconds=10,
            extension_limit_seconds=60,
            allow_extension=True,
            custom_metadata={"key": "value"},
        )

        # Test accessing multiple properties in sequence
        def access_all_properties():
            return {
                "timeout_seconds": timeout.timeout_seconds,
                "warning_threshold": timeout.warning_threshold_seconds,
                "extension_limit": timeout.extension_limit_seconds,
                "custom_properties": timeout.custom_properties,
                "timeout_timedelta": timeout.timeout_timedelta,
                "is_strict": timeout.is_strict,
                "allow_extension": timeout.allow_extension,
            }

        access_time = self.time_operation(access_all_properties, 50)

        # Should be fast due to caching optimizations
        assert (
            access_time < 0.005
        ), f"Property access pattern ({access_time:.6f}s) should be optimized"

    def test_memory_usage_optimization(self):
        """Test that optimizations don't create excessive memory overhead."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create many timeout objects to test memory usage
        timeouts = []
        for i in range(100):
            timeout = ModelTimeout(
                timeout_seconds=30 + i,
                custom_metadata={f"key_{i}": f"value_{i}"},
            )
            # Access cached properties to populate caches
            _ = timeout.custom_properties
            timeouts.append(timeout)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB for 100 objects)
        max_acceptable_increase = 50 * 1024 * 1024  # 50MB
        assert memory_increase < max_acceptable_increase, (
            f"Memory usage increased by {memory_increase / 1024 / 1024:.1f}MB, "
            f"which exceeds the acceptable limit of {max_acceptable_increase / 1024 / 1024}MB"
        )


class TestPerformanceBenchmarks:
    """Integration tests for performance benchmarks."""

    def test_benchmark_script_exists(self):
        """Test that benchmark scripts exist and are executable."""
        from pathlib import Path

        benchmark_script = (
            Path(__file__).parent.parent.parent
            / "scripts/performance/benchmark_serialization.py"
        )
        assert benchmark_script.exists(), "Serialization benchmark script should exist"

        import_script = (
            Path(__file__).parent.parent.parent
            / "scripts/performance/analyze_imports.py"
        )
        assert import_script.exists(), "Import analysis script should exist"

    def test_performance_regression_detection(self):
        """Test that we can detect performance regressions."""
        # This would be used in CI/CD to detect performance regressions

        timeout = ModelTimeout(timeout_seconds=30)

        # Set baseline expectations
        max_property_access_time = 0.001  # 1ms
        max_creation_time = 0.01  # 10ms

        # Test property access performance
        def access_timeout_seconds():
            return timeout.timeout_seconds

        access_time = time.perf_counter()
        for _ in range(100):
            access_timeout_seconds()
        access_time = (time.perf_counter() - access_time) / 100

        assert (
            access_time < max_property_access_time
        ), f"Property access regression detected: {access_time:.6f}s > {max_property_access_time}s"

        # Test creation performance
        def create_timeout():
            return ModelTimeout(timeout_seconds=30)

        creation_time = time.perf_counter()
        for _ in range(10):
            create_timeout()
        creation_time = (time.perf_counter() - creation_time) / 10

        assert (
            creation_time < max_creation_time
        ), f"Creation regression detected: {creation_time:.6f}s > {max_creation_time}s"

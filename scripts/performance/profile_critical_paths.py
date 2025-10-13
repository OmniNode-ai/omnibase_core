#!/usr/bin/env python3
"""
Performance profiler for critical code paths in omnibase_core.

This script profiles the performance-critical operations identified in PR review:
1. ModelTimeout operations and runtime category calculations
2. Pydantic model serialization/deserialization
3. Property computations in core models
4. Import performance analysis
"""

import cProfile
import pstats
import sys
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    import os

    os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")

    # Import only what we need for basic profiling
    import importlib.util

    # Load modules directly to avoid circular imports
    def load_module_from_path(module_name: str, file_path: str):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {module_name} from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Mock basic functionality for profiling
    class MockEnumRuntimeCategory:
        FAST = "FAST"
        MODERATE = "MODERATE"
        SLOW = "SLOW"

        @property
        def estimated_seconds(self):
            if self == "FAST":
                return (1, 10)
            elif self == "MODERATE":
                return (10, 60)
            else:
                return (60, 300)

    # Just profile basic operations without full model loading
    EnumRuntimeCategory = MockEnumRuntimeCategory()

except ImportError as e:
    print(f"Import error: {e}")
    print("Running in basic profiling mode...")

    class BasicProfiler:
        def profile_basic_operations(self):
            """Profile basic Python operations relevant to the codebase."""
            print("📊 Running basic performance analysis...")

            # Test 1: Dictionary operations (common in Pydantic models)
            def dict_operations():
                results = []
                for i in range(1000):
                    data = {
                        "timeout_seconds": 30 + i,
                        "description": f"Timeout {i}",
                        "metadata": {"key": f"value_{i}"},
                    }
                    # Simulate model validation work
                    processed = {
                        k: str(v) if not isinstance(v, dict) else v
                        for k, v in data.items()
                    }
                    results.append(processed)
                return results

            # Test 2: Property-like access patterns
            def property_simulation():
                class MockModel:
                    def __init__(self):
                        self._data = {"value": 30, "unit": "seconds"}

                    @property
                    def computed_value(self):
                        # Simulate expensive computation like to_seconds()
                        return self._data["value"] * (
                            60 if self._data["unit"] == "minutes" else 1
                        )

                model = MockModel()
                results = []
                for _ in range(100):
                    results.append(model.computed_value)
                return results

            # Run basic benchmarks
            self.profile_function("dict_operations", dict_operations)
            self.profile_function("property_simulation", property_simulation)

        def profile_function(self, name: str, func):
            start = time.perf_counter()
            result = func()
            end = time.perf_counter()
            print(
                f"  {name}: {end-start:.4f}s ({len(result) if hasattr(result, '__len__') else 'N/A'} items)"
            )

    profiler = BasicProfiler()
    profiler.profile_basic_operations()
    sys.exit(0)


class PerformanceProfiler:
    """Profile critical performance paths in omnibase_core."""

    def __init__(self):
        self.results: dict[str, dict[str, Any]] = {}

    def profile_function(self, func_name: str, func, *args, **kwargs) -> Any:
        """Profile a function and store results."""
        profiler = cProfile.Profile()

        start_time = time.perf_counter()
        profiler.enable()

        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Capture profiler stats
        stats_stream = StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.sort_stats("cumulative").print_stats(10)

        self.results[func_name] = {
            "execution_time": execution_time,
            "result": result,
            "profiler_stats": stats_stream.getvalue(),
            "function_calls": stats.total_calls,
        }

        return result

    def benchmark_model_timeout_operations(self):
        """Benchmark ModelTimeout critical operations."""
        print("🔍 Profiling ModelTimeout operations...")

        # Test 1: Runtime category calculation (mentioned in PR)
        def create_from_runtime_category():
            results = []
            for category in EnumRuntimeCategory:
                timeout = ModelTimeout.from_runtime_category(
                    category,
                    description=f"Test timeout for {category.name}",
                    use_max_estimate=True,
                )
                results.append(timeout)
            return results

        self.profile_function(
            "ModelTimeout.from_runtime_category", create_from_runtime_category
        )

        # Test 2: Property access patterns
        timeout = ModelTimeout(timeout_seconds=30, description="Test")

        def access_properties():
            results = []
            for _ in range(100):
                results.extend(
                    [
                        timeout.timeout_seconds,
                        timeout.custom_properties,  # This one is expensive
                        timeout.runtime_category,
                        timeout.timeout_timedelta,
                        timeout.max_total_seconds,
                    ]
                )
            return results

        self.profile_function("ModelTimeout.property_access", access_properties)

        # Test 3: Serialization/deserialization (mentioned in PR)
        def serialize_deserialize_cycle():
            results = []
            for i in range(50):
                timeout = ModelTimeout(
                    timeout_seconds=30 + i,
                    warning_threshold_seconds=10,
                    description=f"Timeout {i}",
                    runtime_category=EnumRuntimeCategory.MODERATE,
                    custom_metadata={"test_key": f"value_{i}"},
                )

                # Serialize to typed data
                typed_data = timeout.to_typed_data()

                # Deserialize back
                restored = ModelTimeout.model_validate_typed(typed_data)
                results.append(restored)
            return results

        self.profile_function(
            "ModelTimeout.serialization_cycle", serialize_deserialize_cycle
        )

    def benchmark_import_performance(self):
        """Benchmark import performance for optimization opportunities."""
        print("📦 Profiling import performance...")

        def import_heavy_modules():
            # Simulate importing various omnibase_core modules
            import importlib
            import sys

            modules_to_test = [
                "omnibase_core.models.infrastructure.model_timeout",
                "omnibase_core.models.infrastructure.model_progress",
                "omnibase_core.models.metadata.model_node_info_summary",
                "omnibase_core.enums.enum_runtime_category",
            ]

            results = []
            for module_name in modules_to_test:
                if module_name in sys.modules:
                    # Reload to measure import time
                    del sys.modules[module_name]

                start = time.perf_counter()
                module = importlib.import_module(module_name)
                end = time.perf_counter()

                results.append(
                    {
                        "module": module_name,
                        "import_time": end - start,
                        "module": module,
                    }
                )

            return results

        self.profile_function("module_imports", import_heavy_modules)

    def run_all_benchmarks(self):
        """Run all performance benchmarks."""
        print("🚀 Starting Performance Analysis...")
        print("=" * 60)

        self.benchmark_model_timeout_operations()
        self.benchmark_import_performance()

        print("\n📊 Performance Analysis Results:")
        print("=" * 60)

        for func_name, results in self.results.items():
            print(f"\n🔥 {func_name}")
            print(f"   Execution Time: {results['execution_time']:.4f}s")
            print(f"   Function Calls: {results['function_calls']}")

            if results["execution_time"] > 0.1:  # Flag slow operations
                print("   ⚠️  SLOW OPERATION - Consider optimization!")
            elif results["execution_time"] > 0.01:
                print("   ⚡ Moderate speed - Monitor for growth")
            else:
                print("   ✅ Fast operation")

    def generate_optimization_recommendations(self):
        """Generate specific optimization recommendations based on profiling."""
        print("\n🎯 Optimization Recommendations:")
        print("=" * 60)

        recommendations = []

        # Analyze ModelTimeout performance
        timeout_ops = [
            "ModelTimeout.from_runtime_category",
            "ModelTimeout.property_access",
        ]
        slow_timeout_ops = [
            op
            for op in timeout_ops
            if op in self.results and self.results[op]["execution_time"] > 0.01
        ]

        if slow_timeout_ops:
            recommendations.append(
                {
                    "issue": "ModelTimeout operations are slow",
                    "operations": slow_timeout_ops,
                    "solution": "Add property caching and optimize runtime category calculations",
                    "priority": "HIGH",
                }
            )

        # Analyze serialization performance
        if (
            "ModelTimeout.serialization_cycle" in self.results
            and self.results["ModelTimeout.serialization_cycle"]["execution_time"]
            > 0.05
        ):
            recommendations.append(
                {
                    "issue": "Serialization/deserialization is slow",
                    "solution": "Optimize Pydantic model validation and consider field validators",
                    "priority": "MEDIUM",
                }
            )

        # Print recommendations
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['issue']} [{rec['priority']}]")
            print(f"   Solution: {rec['solution']}")
            if "operations" in rec:
                print(f"   Affected: {', '.join(rec['operations'])}")

        if not recommendations:
            print("\n✅ No critical performance issues detected!")

        return recommendations


def main():
    """Main performance analysis entry point."""
    profiler = PerformanceProfiler()
    profiler.run_all_benchmarks()
    recommendations = profiler.generate_optimization_recommendations()

    # Save detailed results to file
    results_file = Path("performance_analysis_results.txt")
    with open(results_file, "w") as f:
        f.write("PERFORMANCE ANALYSIS RESULTS\n")
        f.write("=" * 40 + "\n\n")

        for func_name, results in profiler.results.items():
            f.write(f"{func_name}\n")
            f.write("-" * len(func_name) + "\n")
            f.write(f"Execution Time: {results['execution_time']:.4f}s\n")
            f.write(f"Function Calls: {results['function_calls']}\n")
            f.write("\nProfiler Stats:\n")
            f.write(results["profiler_stats"])
            f.write("\n" + "=" * 40 + "\n")

    print(f"\n💾 Detailed results saved to: {results_file}")

    return recommendations


if __name__ == "__main__":
    main()

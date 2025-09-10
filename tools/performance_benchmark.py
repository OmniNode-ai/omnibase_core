#!/usr/bin/env python3
"""
Performance Benchmarking Framework for Lazy Evaluation Optimization

Measures memory usage, execution time, and serialization performance
for model_dump() operations before and after lazy evaluation optimization.
"""

import gc
import statistics
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omnibase_core.core.adapters.adapter_bus_shim import ModelEventBusMessage
from omnibase_core.core.protocols.protocol_onex_validation import ModelOnexMetadata
from omnibase_core.model.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.model.core.model_onex_security_context import (
    ModelOnexSecurityContext,
)
from omnibase_core.model.core.model_semver import ModelSemVer


class PerformanceBenchmark:
    """Performance benchmarking framework for lazy evaluation optimization."""

    def __init__(self):
        """Initialize benchmarking framework."""
        self.results: Dict[str, Dict[str, Any]] = {}
        self.sample_size = 100
        self.warmup_runs = 10

    def create_test_envelope(self, complexity: str = "medium") -> ModelOnexEnvelope:
        """Create test envelope with varying complexity levels."""

        # Create test message
        test_message = ModelEventBusMessage(
            message_id=str(uuid4()),
            event_type="test.performance",
            payload={
                "test_data": "x"
                * (
                    100
                    if complexity == "small"
                    else 1000 if complexity == "medium" else 10000
                )
            },
            source_service="test_service",
            timestamp=datetime.utcnow(),
        )

        # Create security context if complex
        security_context = None
        if complexity != "small":
            security_context = ModelOnexSecurityContext(
                user_id="test_user",
                permissions=["read", "write"] * (5 if complexity == "large" else 2),
                token="test_token_" + "x" * (100 if complexity == "large" else 10),
            )

        # Create metadata if complex
        metadata = None
        if complexity == "large":
            metadata = ModelOnexMetadata(additional_data={"key": "value"} * 50)

        return ModelOnexEnvelope(
            envelope_id=uuid4(),
            correlation_id=uuid4(),
            timestamp=datetime.utcnow(),
            source_tool="test_source",
            target_tool="test_target",
            operation="test_operation",
            payload=test_message,
            payload_type="test.performance",
            security_context=security_context,
            metadata=metadata,
            onex_version=ModelSemVer(major=1, minor=0, patch=0),
            envelope_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    def measure_memory_and_time(
        self,
        operation: Callable[[], Any],
        description: str,
        warmup: int = 10,
        samples: int = 100,
    ) -> Dict[str, float]:
        """
        Measure memory usage and execution time for an operation.

        Args:
            operation: Function to benchmark
            description: Description of the operation
            warmup: Number of warmup runs
            samples: Number of measurement samples

        Returns:
            Dictionary with performance metrics
        """
        # Warmup runs
        for _ in range(warmup):
            operation()

        gc.collect()

        # Memory and time measurements
        memory_samples: List[float] = []
        time_samples: List[float] = []

        for _ in range(samples):
            gc.collect()

            # Start memory tracking
            tracemalloc.start()
            start_time = time.perf_counter()

            # Execute operation
            result = operation()

            # Measure
            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Record measurements
            time_samples.append((end_time - start_time) * 1000)  # Convert to ms
            memory_samples.append(peak / 1024 / 1024)  # Convert to MB

            # Clean up
            del result
            gc.collect()

        return {
            "avg_time_ms": statistics.mean(time_samples),
            "min_time_ms": min(time_samples),
            "max_time_ms": max(time_samples),
            "std_time_ms": (
                statistics.stdev(time_samples) if len(time_samples) > 1 else 0
            ),
            "avg_memory_mb": statistics.mean(memory_samples),
            "min_memory_mb": min(memory_samples),
            "max_memory_mb": max(memory_samples),
            "std_memory_mb": (
                statistics.stdev(memory_samples) if len(memory_samples) > 1 else 0
            ),
            "samples": samples,
            "description": description,
        }

    def benchmark_envelope_to_dict(
        self, complexity: str = "medium"
    ) -> Dict[str, Dict[str, float]]:
        """
        Benchmark envelope to_dict() method with and without lazy evaluation.

        Args:
            complexity: Test data complexity level

        Returns:
            Performance comparison results
        """
        envelope = self.create_test_envelope(complexity)

        print(f"Benchmarking envelope to_dict() - {complexity} complexity...")

        # Benchmark lazy evaluation implementation
        lazy_metrics = self.measure_memory_and_time(
            lambda: envelope.to_dict(),
            f"Envelope.to_dict() with lazy evaluation ({complexity})",
        )

        # Benchmark traditional implementation (simulate old behavior)
        def traditional_to_dict():
            """Simulate old to_dict without lazy evaluation."""
            return {
                "envelope_id": str(envelope.envelope_id),
                "correlation_id": str(envelope.correlation_id),
                "timestamp": envelope.timestamp.isoformat(),
                "source_tool": envelope.source_tool or "",
                "target_tool": envelope.target_tool or "",
                "operation": envelope.operation or "",
                "payload": str(envelope.payload.model_dump()),  # Direct model_dump()
                "payload_type": envelope.payload_type or "",
                "security_context": (
                    str(envelope.security_context.model_dump())
                    if envelope.security_context
                    else ""
                ),
                "metadata": (
                    str(envelope.metadata.model_dump()) if envelope.metadata else ""
                ),
                "onex_version": str(envelope.onex_version),
                "envelope_version": str(envelope.envelope_version),
                "request_id": envelope.request_id or "",
                "trace_id": envelope.trace_id or "",
                "span_id": envelope.span_id or "",
                "priority": str(envelope.priority),
                "timeout_seconds": (
                    str(envelope.timeout_seconds) if envelope.timeout_seconds else ""
                ),
                "retry_count": str(envelope.retry_count),
            }

        traditional_metrics = self.measure_memory_and_time(
            traditional_to_dict,
            f"Envelope.to_dict() traditional approach ({complexity})",
        )

        return {
            "lazy_evaluation": lazy_metrics,
            "traditional": traditional_metrics,
            "improvement": {
                "memory_reduction_percent": (
                    (
                        traditional_metrics["avg_memory_mb"]
                        - lazy_metrics["avg_memory_mb"]
                    )
                    / traditional_metrics["avg_memory_mb"]
                    * 100
                ),
                "time_reduction_percent": (
                    (traditional_metrics["avg_time_ms"] - lazy_metrics["avg_time_ms"])
                    / traditional_metrics["avg_time_ms"]
                    * 100
                ),
                "memory_efficiency_ratio": traditional_metrics["avg_memory_mb"]
                / lazy_metrics["avg_memory_mb"],
            },
        }

    def benchmark_model_dump_patterns(self) -> Dict[str, Any]:
        """Benchmark various model_dump usage patterns."""
        print("Benchmarking model_dump patterns...")

        envelope = self.create_test_envelope("large")

        patterns = {
            "direct_model_dump": lambda: envelope.model_dump(),
            "nested_serialization": lambda: {
                "payload": envelope.payload.model_dump(),
                "security": (
                    envelope.security_context.model_dump()
                    if envelope.security_context
                    else None
                ),
                "metadata": (
                    envelope.metadata.model_dump() if envelope.metadata else None
                ),
            },
            "lazy_serialization": lambda: {
                "payload": envelope.lazy_string_conversion(
                    envelope.payload, "payload"
                )(),
                "security": (
                    envelope.lazy_string_conversion(
                        envelope.security_context, "security"
                    )()
                    if envelope.security_context
                    else ""
                ),
                "metadata": (
                    envelope.lazy_string_conversion(envelope.metadata, "metadata")()
                    if envelope.metadata
                    else ""
                ),
            },
        }

        results = {}
        for pattern_name, operation in patterns.items():
            results[pattern_name] = self.measure_memory_and_time(
                operation, f"Model dump pattern: {pattern_name}"
            )

        return results

    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        print("🚀 Starting comprehensive performance benchmark...")
        print("=" * 60)

        results = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "samples": self.sample_size,
                "warmup_runs": self.warmup_runs,
                "python_version": sys.version,
                "benchmark_version": "1.0.0",
            },
            "envelope_benchmarks": {},
            "model_dump_patterns": {},
            "cache_effectiveness": {},
        }

        # Benchmark envelope to_dict with different complexity levels
        for complexity in ["small", "medium", "large"]:
            results["envelope_benchmarks"][complexity] = (
                self.benchmark_envelope_to_dict(complexity)
            )

        # Benchmark model_dump patterns
        results["model_dump_patterns"] = self.benchmark_model_dump_patterns()

        # Test cache effectiveness
        envelope = self.create_test_envelope("medium")
        cache_stats_initial = envelope.get_lazy_cache_stats()

        # Trigger lazy evaluations
        envelope.to_dict()
        cache_stats_after = envelope.get_lazy_cache_stats()

        results["cache_effectiveness"] = {
            "initial": cache_stats_initial,
            "after_usage": cache_stats_after,
            "cache_utilization": cache_stats_after.get("cache_hit_ratio", 0.0),
        }

        return results

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print benchmark results in a readable format."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)

        # Print envelope benchmarks
        print("\n🔍 Envelope to_dict() Performance:")
        print("-" * 40)
        for complexity, data in results["envelope_benchmarks"].items():
            improvement = data["improvement"]
            print(f"\n{complexity.upper()} Complexity:")
            print(f"  Memory Reduction: {improvement['memory_reduction_percent']:.1f}%")
            print(f"  Time Reduction:   {improvement['time_reduction_percent']:.1f}%")
            print(f"  Efficiency Ratio: {improvement['memory_efficiency_ratio']:.2f}x")

            lazy = data["lazy_evaluation"]
            traditional = data["traditional"]
            print(
                f"  Lazy Avg:     {lazy['avg_time_ms']:.2f}ms, {lazy['avg_memory_mb']:.2f}MB"
            )
            print(
                f"  Traditional:  {traditional['avg_time_ms']:.2f}ms, {traditional['avg_memory_mb']:.2f}MB"
            )

        # Print cache effectiveness
        print("\n💾 Cache Effectiveness:")
        print("-" * 40)
        cache_data = results["cache_effectiveness"]
        print(f"  Initial entries: {cache_data['initial']['total_entries']}")
        print(f"  After usage:     {cache_data['after_usage']['total_entries']}")
        print(f"  Cache hit ratio: {cache_data['cache_utilization']:.2%}")
        print(
            f"  Memory efficiency: {cache_data['after_usage'].get('memory_efficiency', 'N/A')}"
        )

        # Calculate overall performance improvement
        total_memory_improvement = 0
        total_time_improvement = 0
        complexity_count = len(results["envelope_benchmarks"])

        for data in results["envelope_benchmarks"].values():
            total_memory_improvement += data["improvement"]["memory_reduction_percent"]
            total_time_improvement += data["improvement"]["time_reduction_percent"]

        avg_memory_improvement = total_memory_improvement / complexity_count
        avg_time_improvement = total_time_improvement / complexity_count

        print("\n🎯 OPTIMIZATION SUCCESS:")
        print("-" * 40)
        print(f"  Average Memory Reduction: {avg_memory_improvement:.1f}%")
        print(f"  Average Time Reduction:   {avg_time_improvement:.1f}%")
        print(
            f"  Target Achievement:       {'✅ ACHIEVED' if avg_memory_improvement >= 60 else '⚠️ PARTIAL'}"
        )

        if avg_memory_improvement >= 60:
            print(f"  🎉 Successfully achieved 60% memory reduction target!")
        else:
            print(f"  📈 Current: {avg_memory_improvement:.1f}%, Target: 60%")

    def save_results(
        self,
        results: Dict[str, Any],
        filename: str = "performance_benchmark_results.json",
    ) -> None:
        """Save results to JSON file."""
        import json

        filepath = Path(__file__).parent / filename
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Results saved to: {filepath}")


def main():
    """Main benchmark execution."""
    try:
        benchmark = PerformanceBenchmark()
        results = benchmark.run_comprehensive_benchmark()
        benchmark.print_results(results)
        benchmark.save_results(results)

        print("\n✅ Performance benchmark completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        print(f"Traceback: {tracemalloc.format_exception(type(e), e, e.__traceback__)}")
        return 1


if __name__ == "__main__":
    exit(main())

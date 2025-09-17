#!/usr/bin/env python3
"""
Simple Performance Test for Lazy Evaluation Mixin

Tests the core lazy evaluation functionality without complex dependencies.
"""

import gc
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import BaseModel

from omnibase_core.mixins.mixin_lazy_evaluation import LazyValue, MixinLazyEvaluation


class TestModel(BaseModel, MixinLazyEvaluation):
    """Test model for performance validation."""

    name: str
    data: str

    def __init__(self, **data):
        """Initialize with lazy evaluation."""
        super().__init__(**data)
        MixinLazyEvaluation.__init__(self)


def measure_operation(
    operation, description: str, samples: int = 50
) -> Dict[str, float]:
    """Measure memory and time for an operation."""
    memory_samples = []
    time_samples = []

    # Warmup
    for _ in range(10):
        operation()

    gc.collect()

    # Measure
    for _ in range(samples):
        gc.collect()

        tracemalloc.start()
        start_time = time.perf_counter()

        result = operation()

        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_samples.append(peak / 1024 / 1024)  # MB
        time_samples.append((end_time - start_time) * 1000)  # ms

        del result
        gc.collect()

    return {
        "avg_memory_mb": sum(memory_samples) / len(memory_samples),
        "avg_time_ms": sum(time_samples) / len(time_samples),
        "description": description,
    }


def test_lazy_evaluation():
    """Test lazy evaluation performance."""
    print("🚀 Testing Lazy Evaluation Performance")
    print("=" * 50)

    # Create test model with large data
    model = TestModel(name="test", data="x" * 10000)  # 10KB data

    # Test lazy model_dump vs direct model_dump
    lazy_stats = measure_operation(lambda: model.lazy_model_dump()(), "Lazy model_dump")

    traditional_stats = measure_operation(
        lambda: model.model_dump(), "Traditional model_dump"
    )

    # Calculate improvements
    memory_reduction = (
        (traditional_stats["avg_memory_mb"] - lazy_stats["avg_memory_mb"])
        / traditional_stats["avg_memory_mb"]
        * 100
    )
    time_improvement = (
        (traditional_stats["avg_time_ms"] - lazy_stats["avg_time_ms"])
        / traditional_stats["avg_time_ms"]
        * 100
    )

    print(f"\n📊 RESULTS:")
    print(f"  Memory Reduction: {memory_reduction:.1f}%")
    print(f"  Time Improvement: {time_improvement:.1f}%")
    print(f"  Lazy Avg Time: {lazy_stats['avg_time_ms']:.2f}ms")
    print(f"  Traditional Avg Time: {traditional_stats['avg_time_ms']:.2f}ms")
    print(f"  Lazy Avg Memory: {lazy_stats['avg_memory_mb']:.2f}MB")
    print(f"  Traditional Avg Memory: {traditional_stats['avg_memory_mb']:.2f}MB")

    # Test cache effectiveness
    print(f"\n💾 CACHE EFFECTIVENESS:")
    initial_stats = model.get_lazy_cache_stats()
    print(f"  Initial cache entries: {initial_stats['total_entries']}")

    # Trigger lazy operations
    model.lazy_model_dump()()
    model.lazy_model_dump()()  # Should use cache

    after_stats = model.get_lazy_cache_stats()
    print(f"  After usage entries: {after_stats['total_entries']}")
    print(f"  Cache hit ratio: {after_stats.get('cache_hit_ratio', 0):.2%}")
    print(f"  Memory efficiency: {after_stats.get('memory_efficiency', 'N/A')}")

    # Test lazy value functionality
    print(f"\n🧪 LAZY VALUE FUNCTIONALITY:")

    def expensive_computation():
        """Simulate expensive computation."""
        return sum(range(10000))

    lazy_value = LazyValue(expensive_computation, cache=True)

    # Test first access (computation)
    start_time = time.perf_counter()
    result1 = lazy_value()
    first_access_time = (time.perf_counter() - start_time) * 1000

    # Test second access (cached)
    start_time = time.perf_counter()
    result2 = lazy_value()
    second_access_time = (time.perf_counter() - start_time) * 1000

    print(f"  First access time: {first_access_time:.2f}ms")
    print(f"  Second access time (cached): {second_access_time:.2f}ms")
    print(f"  Cache speedup: {first_access_time / second_access_time:.1f}x")
    print(f"  Results identical: {result1 == result2}")

    # Validation
    success = True

    if lazy_stats["avg_time_ms"] > 2000:  # 2 second target
        print(
            f"❌ Response time target missed: {lazy_stats['avg_time_ms']:.2f}ms > 2000ms"
        )
        success = False
    else:
        print(
            f"✅ Response time target met: {lazy_stats['avg_time_ms']:.2f}ms < 2000ms"
        )

    if second_access_time >= first_access_time:
        print(f"❌ Cache not working effectively")
        success = False
    else:
        print(
            f"✅ Cache working effectively: {first_access_time / second_access_time:.1f}x speedup"
        )

    print(f"\n🎯 OVERALL RESULT: {'SUCCESS' if success else 'NEEDS IMPROVEMENT'}")

    return success


if __name__ == "__main__":
    success = test_lazy_evaluation()
    sys.exit(0 if success else 1)

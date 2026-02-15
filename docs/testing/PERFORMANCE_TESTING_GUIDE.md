> **Navigation**: [Home](../INDEX.md) > Testing > Performance Testing Guide

# Performance Testing Guide

**Location**: `tests/performance/`

**Status**: ✅ Active - Performance testing framework

**Last Updated**: 2025-12-16

---

## Table of Contents

1. [Overview](#overview)
2. [When to Add Performance Tests](#when-to-add-performance-tests)
3. [Performance Test Categories](#performance-test-categories)
4. [Writing Performance Tests](#writing-performance-tests)
5. [Statistical Significance](#statistical-significance)
6. [Benchmark Stability](#benchmark-stability)
7. [Performance Regression Detection](#performance-regression-detection)
8. [Best Practices](#best-practices)
9. [Common Patterns](#common-patterns)
10. [CI Integration](#ci-integration)
11. [Examples from Codebase](#examples-from-codebase)

---

## Overview

Performance testing in omnibase_core ensures that critical operations remain fast and scalable as the codebase evolves. Performance tests complement functional tests by measuring timing, memory usage, and scalability characteristics.

### Goals

1. **Regression Detection**: Catch performance degradation before it reaches production
2. **Scalability Validation**: Verify linear scaling for data size increases
3. **Overhead Measurement**: Quantify the cost of new features
4. **Resource Usage**: Monitor memory consumption and resource efficiency

### Non-Goals

1. **Micro-optimization**: Not for optimizing every line of code
2. **Absolute Speed**: Focus on acceptable performance, not theoretical maximum
3. **Hardware Comparison**: Not for comparing different machines
4. **Production Profiling**: Use APM tools (Datadog, New Relic) for production

---

## When to Add Performance Tests

### ✅ Add Performance Tests When:

1. **Critical Path Operations** - Operations that run frequently (>1000x/sec)
   - Event bus serialization/deserialization
   - Model creation and validation
   - State machine transitions
   - Dependency resolution

2. **Large Data Processing** - Operations that scale with data size
   - Bulk model creation (100s-10,000s of items)
   - Batch serialization
   - Large dependency graphs
   - Workflow execution with many nodes

3. **Performance-Sensitive Features** - Features where latency matters
   - HTTP request handling (p95 < 50ms)
   - Event processing (p99 < 100ms)
   - Cache operations (p50 < 1ms)
   - Database queries (p95 < 10ms)

4. **New Optimizations** - Verify optimizations actually improve performance
   - Caching implementations
   - Pre-compiled regex patterns
   - Lazy loading strategies
   - Memory pooling

5. **Known Bottlenecks** - Areas identified by profiling
   - Pydantic model creation
   - JSON serialization
   - UUID generation
   - Complex validation logic

### ❌ Don't Add Performance Tests For:

1. **Trivial Operations** - Operations that are inherently fast (< 1µs)
   - Simple getters/setters
   - Enum comparisons
   - Boolean flags

2. **I/O-Bound Operations** - Performance depends on external systems
   - Database queries (unless mocked)
   - Network requests
   - File system operations (unless measuring serialization)

3. **One-Time Operations** - Operations that run once per process
   - Service initialization
   - Configuration loading
   - Module imports

4. **Non-Deterministic Operations** - Operations with high variance
   - Random number generation
   - External API calls
   - Network latency measurements

---

## Performance Test Categories

### 1. Microbenchmarks

**What**: Single operation timing (< 1ms)

**When**: Testing individual functions or methods

**Example**: Field validation performance

```python
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
class TestFieldValidationPerformance:
    """Microbenchmark for field-level validation."""

    def time_operation(self, func, iterations: int = 1000):
        """Time operation with high iteration count for stability."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            times.append(time.perf_counter() - start)
        return mean(times)

    def test_validation_performance_field_level(self):
        """Benchmark field-level validation performance.

        Performance Baseline: < 0.1ms per field
        """
        def create_with_validation():
            return ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.5,  # Triggers validation
                items_processed=100,
            )

        avg_time = self.time_operation(create_with_validation, 1000)
        avg_time_ms = avg_time * 1000

        # Each creation validates 2 fields
        per_field_ms = avg_time_ms / 2

        assert per_field_ms < 0.1, (
            f"Field validation took {per_field_ms:.3f}ms, expected < 0.1ms"
        )
```

### 2. Integration Benchmarks

**What**: Multiple operations together (1-100ms)

**When**: Testing realistic workflows

**Example**: Round-trip serialization

```python
def test_round_trip_performance(self):
    """Benchmark full round-trip serialization/deserialization.

    Validates end-to-end performance for common event bus workflow:
    Create → Serialize to JSON → Deserialize from JSON → Access fields

    Performance Baseline: < 20ms for 100 items
    """
    operation_id = uuid4()
    result_data = {
        "items": [{"id": i, "value": f"item_{i}"} for i in range(100)],
        "metadata": {"total": 100},
    }

    def round_trip():
        # Create
        output = ModelReducerOutput[dict](
            result=result_data,
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=42.5,
            items_processed=100,
        )

        # Serialize to JSON
        json_data = output.model_dump_json()

        # Deserialize from JSON
        restored = ModelReducerOutput[dict].model_validate_json(json_data)

        # Access fields (verify no lazy loading overhead)
        _ = restored.result
        _ = restored.operation_id
        return restored

    avg_time = self.time_operation(round_trip, 50)
    avg_time_ms = avg_time * 1000

    assert avg_time_ms < 20.0, (
        f"Round-trip took {avg_time_ms:.2f}ms, expected < 20ms"
    )
```

### 3. Scalability Benchmarks

**What**: Performance vs data size (parametrized)

**When**: Validating linear scaling

**Example**: Model creation with varying data sizes

```python
@pytest.mark.parametrize(
    ("data_size", "max_time_ms"),
    [
        pytest.param(10, 1.0, id="small_10_items"),
        pytest.param(100, 2.0, id="medium_100_items"),
        pytest.param(1000, 10.0, id="large_1000_items"),
        pytest.param(10000, 50.0, id="xlarge_10000_items"),
    ],
)
def test_model_creation_performance(
    self, data_size: int, max_time_ms: float
) -> None:
    """Benchmark model creation with varying data sizes.

    Validates linear scaling: 10x data → ~10x time

    Threshold Rationale:
        - 10 items: UUID generation + validation ≈ 1ms
        - 100 items: Linear scaling + overhead ≈ 2ms
        - 1000 items: Pydantic validation dominates ≈ 10ms
        - 10000 items: Memory allocation + GC ≈ 50ms
    """
    # ... test implementation
```

### 4. Memory Benchmarks

**What**: Memory usage measurement (RSS)

**When**: Testing memory efficiency and leak detection

**Example**: Memory usage with varying data sizes

```python
def test_memory_usage(self, data_size: int, max_memory_mb: int):
    """Benchmark memory usage with varying data sizes.

    Uses psutil to measure RSS (Resident Set Size).

    Performance Baseline:
        - 10 items: < 1MB
        - 100 items: < 5MB
        - 1000 items: < 20MB
        - 10000 items: < 100MB
    """
    import os
    import gc
    import psutil

    process = psutil.Process(os.getpid())

    # Force garbage collection before measurement
    gc.collect()
    initial_memory = process.memory_info().rss

    # Create objects
    outputs = []
    for _ in range(10):
        result_data = {
            "items": [{"id": i} for i in range(data_size)],
        }
        output = ModelReducerOutput[dict](
            result=result_data,
            operation_id=uuid4(),
            # ... other fields
        )
        outputs.append(output)

    gc.collect()
    final_memory = process.memory_info().rss
    memory_increase_mb = (final_memory - initial_memory) / 1024 / 1024

    assert memory_increase_mb < max_memory_mb, (
        f"Memory usage increased by {memory_increase_mb:.2f}MB, "
        f"expected < {max_memory_mb}MB"
    )
```

### 5. Overhead Benchmarks

**What**: Percentage overhead of feature additions

**When**: Measuring cost of optional features

**Example**: Source node ID overhead

```python
def test_creation_time_overhead(self):
    """Test envelope creation time with and without source_node_id.

    Expected: < 200% overhead (primary cost is UUID generation)
    """
    # Time creation without source_node_id
    mean_without, stdev_without = self.time_operation(
        self.create_envelope_without_source_node, iterations=100
    )

    # Time creation with source_node_id
    mean_with, stdev_with = self.time_operation(
        self.create_envelope_with_source_node, iterations=100
    )

    # Calculate overhead percentage
    overhead_pct = ((mean_with - mean_without) / mean_without) * 100

    assert overhead_pct < 200.0, (
        f"source_node_id overhead ({overhead_pct:.2f}%) exceeds 200%"
    )

    # Ensure absolute time remains fast
    assert mean_with < 0.01, (
        f"Absolute creation time ({mean_with * 1000:.4f}ms) exceeds 10ms"
    )
```

---

## Writing Performance Tests

### Test Structure Template

```python
import time
from statistics import mean, stdev
import pytest

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(120)  # Prevent infinite hangs
class TestMyFeaturePerformance:
    """Performance tests for MyFeature.

    Note:
    - Marked as @slow due to performance timing tests
    - Timeout (120s) for performance measurement tests
    """

    def time_operation(
        self,
        func: Callable[[], Any],
        iterations: int = 100,
        warmup: int = 5
    ) -> tuple[float, float]:
        """Time an operation with warmup and return (mean, stdev).

        Args:
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Warmup iterations (not counted)

        Returns:
            Tuple of (mean_time, stdev_time) in seconds
        """
        # Warmup phase (prime CPU cache)
        for _ in range(warmup):
            func()

        # Actual measurement
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)

        return mean(times), stdev(times)

    @pytest.mark.parametrize(
        ("data_size", "max_time_ms"),
        [
            pytest.param(10, 1.0, id="small"),
            pytest.param(100, 5.0, id="medium"),
            pytest.param(1000, 50.0, id="large"),
        ],
    )
    def test_operation_performance(
        self, data_size: int, max_time_ms: float
    ):
        """Benchmark operation with varying data sizes.

        Performance Baseline:
            - 10 items: < 1ms
            - 100 items: < 5ms
            - 1000 items: < 50ms

        Threshold Rationale:
            - Small: Validation overhead + UUID generation
            - Medium: Linear scaling from small
            - Large: Pydantic validation dominates + GC triggers

        See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md
        """
        def operation():
            # Your operation here
            pass

        # Fewer iterations for larger data
        iterations = max(10, 100 // (data_size // 10))
        avg_time, _ = self.time_operation(operation, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"Operation with {data_size} items took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )
```

### Required Test Markers

```python
@pytest.mark.performance  # Enable/disable performance tests
@pytest.mark.slow         # CI splits slow tests separately
@pytest.mark.timeout(120) # Prevent infinite loops
```

### Timing Best Practices

1. **Use `time.perf_counter()`** - High-resolution, monotonic timer
   ```python
   start = time.perf_counter()
   operation()
   duration = time.perf_counter() - start
   ```

2. **Include Warmup Iterations** - Prime CPU cache, JIT warmup
   ```python
   for _ in range(5):
       operation()  # Not counted

   # Now measure
   times = []
   for _ in range(100):
       start = time.perf_counter()
       operation()
       times.append(time.perf_counter() - start)
   ```

3. **Report Mean and StdDev** - Shows variance and reliability
   ```python
   from statistics import mean, stdev

   avg_time = mean(times)
   std_time = stdev(times)

   print(f"Average: {avg_time * 1000:.4f}ms ± {std_time * 1000:.4f}ms")
   ```

4. **Adjust Iterations by Scale** - Fewer iterations for large data
   ```python
   iterations = max(10, 100 // (data_size // 10))
   # data_size=10 → 100 iterations
   # data_size=100 → 100 iterations
   # data_size=1000 → 10 iterations
   ```

---

## Statistical Significance

### Why It Matters

Performance measurements have inherent variance due to:
- CPU scheduling (other processes)
- Cache effects (cold vs warm)
- Garbage collection timing
- System load

**Goal**: Detect real regressions while tolerating natural variance.

### Statistical Tests

#### 1. Confidence Intervals (95% CI)

```python
from statistics import mean, stdev
import math

def confidence_interval_95(times):
    """Calculate 95% confidence interval."""
    n = len(times)
    avg = mean(times)
    std = stdev(times)
    margin = 1.96 * (std / math.sqrt(n))  # 95% CI

    return avg - margin, avg + margin

# Usage
times_before = [0.005, 0.0052, 0.0048, ...]  # 100 measurements
times_after = [0.0055, 0.0058, 0.0053, ...]  # 100 measurements

ci_before = confidence_interval_95(times_before)
ci_after = confidence_interval_95(times_after)

# If CIs don't overlap → significant change
if ci_after[0] > ci_before[1]:
    print("Significant regression detected")
```

#### 2. Coefficient of Variation (CV)

```python
def coefficient_of_variation(times):
    """Measure relative variance (lower is better)."""
    return stdev(times) / mean(times)

cv = coefficient_of_variation(times)

# CV < 0.05 → Very stable (5% variance)
# CV < 0.10 → Stable (10% variance)
# CV < 0.20 → Acceptable (20% variance)
# CV > 0.20 → Unstable (need more iterations)
```

#### 3. Minimum Sample Size

```python
def required_iterations(cv_target=0.05, confidence=0.95):
    """Calculate required iterations for target CV.

    Args:
        cv_target: Target coefficient of variation (0.05 = 5%)
        confidence: Confidence level (0.95 = 95%)

    Returns:
        Minimum number of iterations needed
    """
    # Rough estimate: n ≈ (2 / cv_target)^2
    # For CV=5%, n ≈ 1600 iterations
    # For CV=10%, n ≈ 400 iterations

    return math.ceil((2 / cv_target) ** 2)

# For microbenchmarks (< 1ms), use 1000+ iterations
# For integration tests (1-100ms), use 50-100 iterations
# For large-scale tests (> 100ms), use 10-20 iterations
```

### Example: Statistically Valid Test

```python
def test_performance_with_statistical_significance(self):
    """Test with statistical validation."""
    iterations = 100  # Enough for 95% CI

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        operation()
        times.append(time.perf_counter() - start)

    avg = mean(times)
    std = stdev(times)
    cv = std / avg

    # Check stability
    assert cv < 0.20, f"Unstable benchmark (CV={cv:.2%}), increase iterations"

    # Check performance
    ci_lower, ci_upper = confidence_interval_95(times)
    threshold_ms = 10.0

    assert ci_upper < threshold_ms / 1000, (
        f"Performance regression: 95% CI upper bound {ci_upper * 1000:.2f}ms "
        f"exceeds {threshold_ms}ms threshold"
    )

    print(f"✅ Performance: {avg * 1000:.2f}ms ± {std * 1000:.2f}ms (CV={cv:.1%})")
```

---

## Benchmark Stability

### Ensuring Repeatability

#### 1. Warmup Iterations

**Why**: First run is always slower (cold cache, JIT compilation)

```python
def benchmark_with_warmup(func, warmup=10, iterations=100):
    """Run benchmark with proper warmup."""
    # Warmup (not measured)
    for _ in range(warmup):
        func()

    # Actual measurement
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)

    return mean(times), stdev(times)
```

#### 2. Garbage Collection Control

**Why**: GC can trigger mid-benchmark, skewing results

```python
import gc

def benchmark_with_gc_control(func, iterations=100):
    """Run benchmark with GC disabled."""
    # Disable automatic GC
    gc.collect()  # Clean up first
    gc.disable()

    try:
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            times.append(time.perf_counter() - start)

        return mean(times), stdev(times)
    finally:
        gc.enable()  # Always re-enable
```

#### 3. Process Isolation

**Why**: Parallel tests interfere with each other

```bash
# Run performance tests serially (no parallel execution)
uv run pytest tests/performance/ -n 0 -v

# Or mark tests as serial-only
@pytest.mark.serial  # Requires pytest-xdist
```

### Handling Variance

#### Environment Variables for CI

```python
import os

def get_threshold(base_threshold_ms: float) -> float:
    """Adjust threshold based on environment."""
    if os.getenv("CI") == "true":
        # CI runners are 2x slower with higher variance
        return base_threshold_ms * 2.0
    else:
        # Local development (faster, more consistent)
        return base_threshold_ms

# Usage
threshold_ms = get_threshold(10.0)  # 10ms local, 20ms CI
```

#### Retry on Flakiness

```python
# conftest.py
import pytest

@pytest.fixture(autouse=True)
def retry_flaky_performance_tests(request):
    """Retry performance tests on flakiness."""
    if "performance" in request.keywords:
        # Allow 2 retries for performance tests
        request.config.option.maxfail = 3
```

---

## Performance Regression Detection

### Automated Regression Detection

#### 1. Baseline Comparison

```python
import json
from pathlib import Path

class PerformanceBaseline:
    """Track performance baselines across commits."""

    def __init__(self, baseline_file: Path = Path("tests/performance/baselines.json")):
        self.baseline_file = baseline_file
        self.baselines = self._load_baselines()

    def _load_baselines(self) -> dict:
        """Load existing baselines."""
        if self.baseline_file.exists():
            return json.loads(self.baseline_file.read_text())
        return {}

    def save_baseline(self, test_name: str, avg_time_ms: float):
        """Save baseline for a test."""
        self.baselines[test_name] = avg_time_ms
        self.baseline_file.write_text(json.dumps(self.baselines, indent=2))

    def check_regression(self, test_name: str, current_time_ms: float, threshold_pct: float = 20.0):
        """Check if current time is a regression."""
        if test_name not in self.baselines:
            # No baseline yet, save current as baseline
            self.save_baseline(test_name, current_time_ms)
            return False

        baseline = self.baselines[test_name]
        regression_pct = ((current_time_ms - baseline) / baseline) * 100

        if regression_pct > threshold_pct:
            return True, f"Regression: {regression_pct:.1f}% slower than baseline ({baseline:.2f}ms)"

        return False, None

# Usage in tests
baseline = PerformanceBaseline()

def test_with_regression_detection(self):
    """Test with automated regression detection."""
    avg_time_ms = self.run_benchmark()

    is_regression, message = baseline.check_regression(
        test_name="test_model_creation",
        current_time_ms=avg_time_ms,
        threshold_pct=20.0  # 20% slower = regression
    )

    assert not is_regression, message
```

#### 2. Trend Analysis

```python
from collections import deque
from datetime import datetime

class PerformanceTrend:
    """Track performance trends over time."""

    def __init__(self, window_size: int = 10):
        self.history: deque = deque(maxlen=window_size)

    def add_measurement(self, avg_time_ms: float):
        """Add a measurement to history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "avg_time_ms": avg_time_ms,
        })

    def detect_trend(self) -> tuple[bool, str]:
        """Detect if performance is degrading over time."""
        if len(self.history) < 5:
            return False, "Insufficient data"

        # Calculate slope (linear regression)
        times = [m["avg_time_ms"] for m in self.history]
        n = len(times)
        x = list(range(n))

        # Simple linear regression
        x_mean = sum(x) / n
        y_mean = sum(times) / n
        slope = sum((x[i] - x_mean) * (times[i] - y_mean) for i in range(n)) / sum((x[i] - x_mean) ** 2 for i in range(n))

        # If slope > 10% of mean, performance is degrading
        if slope > (y_mean * 0.1):
            return True, f"Performance degrading at {slope:.3f}ms per measurement"

        return False, "Performance stable"
```

### Git Bisect for Regressions

```bash
# Find the commit that introduced a regression

# Start bisect
git bisect start
git bisect bad HEAD  # Current commit is slow
git bisect good v0.3.6  # Known good version

# Git checks out commits for testing
uv run pytest tests/performance/test_model_reducer_output_benchmarks.py \
    -k "test_model_creation_performance" -x

# Mark each commit
git bisect good  # If test passes
git bisect bad   # If test fails

# Git will identify the problematic commit
```

---

## Best Practices

### ✅ Do

1. **Use High-Resolution Timers**
   ```python
   start = time.perf_counter()  # ✅ Monotonic, high-resolution
   # NOT time.time()  # ❌ Can go backwards, low resolution
   ```

2. **Include Warmup Iterations**
   ```python
   for _ in range(10):
       operation()  # Warmup (not measured)
   ```

3. **Report Mean AND StdDev**
   ```python
   print(f"{avg * 1000:.2f}ms ± {std * 1000:.2f}ms")
   ```

4. **Document Threshold Rationale**
   ```python
   """
   Threshold Rationale:
       - UUID generation: 3 UUIDs × 10µs = 30µs
       - Pydantic validation: 5 fields × 100µs = 500µs
       - Nested structure: ~4ms for 100-item list
       - Total: ~5ms + margin = 10ms threshold
   """
   ```

5. **Use Parametrize for Scale Testing**
   ```python
   @pytest.mark.parametrize("data_size", [10, 100, 1000, 10000])
   ```

6. **Control Garbage Collection**
   ```python
   gc.collect()  # Clean up before measurement
   gc.disable()  # Disable during measurement
   ```

### ❌ Don't

1. **Use `time.time()`** - Low resolution, non-monotonic
2. **Skip Warmup** - First run is always slower
3. **Single Iteration** - Too much variance
4. **Mix Operations** - Hard to debug which part is slow
5. **Ignore Variance** - CV > 20% means unstable benchmark
6. **Test in Parallel** - Other tests interfere with timing

---

## Common Patterns

### Pattern 1: Scalability Test

```python
@pytest.mark.parametrize(
    ("data_size", "max_time_ms"),
    [
        pytest.param(10, 1.0, id="small"),
        pytest.param(100, 2.0, id="medium"),
        pytest.param(1000, 10.0, id="large"),
        pytest.param(10000, 50.0, id="xlarge"),
    ],
)
def test_scalability(self, data_size: int, max_time_ms: float):
    """Test that operation scales linearly with data size."""
    def operation():
        return create_model_with_n_items(data_size)

    iterations = max(10, 100 // (data_size // 10))
    avg_time_ms = self.time_operation(operation, iterations) * 1000

    assert avg_time_ms < max_time_ms, (
        f"Operation with {data_size} items took {avg_time_ms:.2f}ms, "
        f"expected < {max_time_ms}ms (linear scaling)"
    )
```

### Pattern 2: Overhead Measurement

```python
def test_feature_overhead(self):
    """Measure overhead of optional feature."""
    # Baseline (without feature)
    mean_without, _ = self.time_operation(
        lambda: create_without_feature(), iterations=100
    )

    # With feature
    mean_with, _ = self.time_operation(
        lambda: create_with_feature(), iterations=100
    )

    # Calculate overhead percentage
    overhead_pct = ((mean_with - mean_without) / mean_without) * 100

    # Assert acceptable overhead
    assert overhead_pct < 50.0, f"Feature overhead ({overhead_pct:.1f}%) too high"

    # Ensure absolute time remains acceptable
    assert mean_with < 0.01, "Absolute time must remain < 10ms"
```

### Pattern 3: Memory Efficiency

```python
def test_memory_efficiency(self):
    """Test memory usage with large data."""
    import os
    import gc
    import psutil

    process = psutil.Process(os.getpid())

    gc.collect()
    initial_memory = process.memory_info().rss

    # Create objects
    objects = [create_object(i) for i in range(1000)]

    gc.collect()
    final_memory = process.memory_info().rss
    memory_mb = (final_memory - initial_memory) / 1024 / 1024

    assert memory_mb < 50, f"Memory usage ({memory_mb:.1f}MB) exceeds 50MB"
```

### Pattern 4: Comparative Benchmark

```python
def test_pydantic_vs_dict_performance(self):
    """Compare Pydantic model vs raw dict performance."""
    # Pydantic model
    pydantic_time = self.time_operation(
        lambda: create_pydantic_model(), iterations=100
    ) * 1000

    # Raw dict
    dict_time = self.time_operation(
        lambda: create_dict(), iterations=100
    ) * 1000

    overhead_ms = pydantic_time - dict_time
    overhead_pct = (overhead_ms / dict_time) * 100

    print(f"Pydantic: {pydantic_time:.2f}ms, Dict: {dict_time:.2f}ms")
    print(f"Overhead: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")

    # Key assertion: absolute time matters, not relative percentage
    assert pydantic_time < 1.0, (
        "Pydantic absolute time must be < 1ms (percentage overhead is expected)"
    )
```

---

## CI Integration

### Skipping in CI (Manual Benchmarks Only)

```python
import os
import pytest

# Skip in CI - manual benchmark only
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Performance benchmarks not reliable in CI. Run manually.",
)
```

### Running in CI (Regression Detection)

```python
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(120)
class TestPerformanceRegression:
    """CI-safe performance regression tests."""

    def test_baseline_performance(self):
        """Regression test with generous thresholds for CI."""
        threshold_ms = 10.0

        if os.getenv("CI") == "true":
            threshold_ms *= 2.0  # Double threshold for CI

        avg_time_ms = self.run_benchmark()

        assert avg_time_ms < threshold_ms, (
            f"Performance regression: {avg_time_ms:.2f}ms exceeds {threshold_ms}ms"
        )
```

### CI Configuration

```yaml
# .github/workflows/test.yml
- name: Run Performance Tests
  run: |
    uv run pytest tests/performance/ \
      -m "performance and not manual" \
      -n 0 \  # No parallelism for performance tests
      --timeout=300 \
      -v
```

---

## Examples from Codebase

### Example 1: Model Reducer Output Benchmarks

**Location**: `tests/performance/test_model_reducer_output_benchmarks.py`

**What it tests**:
- Model creation performance (10-10,000 items)
- Serialization/deserialization (JSON and dict)
- Field validation overhead
- Memory usage
- Round-trip workflows

**Key patterns**:
- Parametrized data sizes
- Threshold rationale in docstrings
- Mean timing with multiple iterations
- Memory measurement with psutil

### Example 2: Source Node ID Overhead

**Location**: `tests/performance/test_source_node_id_overhead.py`

**What it tests**:
- Creation time overhead (with/without optional field)
- Serialization overhead
- Memory footprint
- Bulk operations (100-10,000 envelopes)

**Key patterns**:
- Warmup iterations (5 before measurement)
- Mean and stdev reporting
- Overhead percentage calculation
- Absolute time validation

### Example 3: Model Dependency Performance

**Location**: `tests/performance/contracts/test_model_dependency_performance.py`

**What it tests**:
- Security validation performance (path traversal, injection)
- Large dependency set creation (5,000 items)
- Memory efficiency
- Stress testing (20 threads, 500 ops/thread)

**Key patterns**:
- Security validation benchmarks
- Large-scale creation (5,000 items)
- Multithreaded stress testing
- Memory profiling with tracemalloc

---

## Related Documentation

- [Performance Benchmark Thresholds](../performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md) - Threshold rationale and adjustment guide
- [CI Monitoring Guide](../ci/CI_MONITORING_GUIDE.md) - CI performance monitoring
- [Parallel Testing](./PARALLEL_TESTING.md) - Test parallelization strategy
- [CI Test Strategy](./CI_TEST_STRATEGY.md) - Overall CI testing approach

---

## Quick Reference

### Test Template Checklist

- [ ] Use `@pytest.mark.performance`
- [ ] Use `@pytest.mark.slow`
- [ ] Use `@pytest.mark.timeout(120)`
- [ ] Include warmup iterations (5-10)
- [ ] Report mean AND stdev
- [ ] Document threshold rationale
- [ ] Use `time.perf_counter()`
- [ ] Parametrize data sizes
- [ ] Test for linear scaling
- [ ] Add inline comments explaining thresholds

### Threshold Selection

1. Run locally 10 times
2. Calculate P95 + 2*StdDev
3. Apply 2x CI multiplier
4. Document in docstring
5. Reference `PERFORMANCE_BENCHMARK_THRESHOLDS.md`

### When Performance Test Fails

1. Check if failure is consistent (regression) or sporadic (variance)
2. Run locally to isolate CI vs code issue
3. Profile with `--profile` if slow everywhere
4. Use `git bisect` to find problematic commit
5. Adjust threshold only if environment changed (CI upgrade, Pydantic update)

---

**Last Updated**: 2025-12-16
**Status**: Active - performance testing framework
**Contact**: @omnibase_core-maintainers

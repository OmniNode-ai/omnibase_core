# Performance Benchmark Thresholds

**Location**: `tests/performance/`

**Status**: ✅ Active performance monitoring

**Last Updated**: 2025-12-16

---

## Overview

This document explains the rationale behind performance benchmark thresholds in omnibase_core, how they're calculated, and how to adjust them for different environments (CI vs local development).

## Table of Contents

1. [Threshold Philosophy](#threshold-philosophy)
2. [Environment Considerations](#environment-considerations)
3. [Threshold Categories](#threshold-categories)
4. [Configuration via Environment Variables](#configuration-via-environment-variables)
5. [Adjusting Thresholds](#adjusting-thresholds)
6. [CI Performance Degradation](#ci-performance-degradation)
7. [Historical Context](#historical-context)

---

## Threshold Philosophy

### Core Principles

1. **Absolute Time Over Relative Overhead**: We care more about absolute execution time (< 1ms) than relative overhead (10x slower). A 1000% overhead is acceptable if absolute time is 0.01ms.

2. **Environment-Aware**: CI runners have different performance characteristics than local machines. Thresholds should be conservative enough for CI while meaningful for local development.

3. **Linear Scaling**: Performance should scale linearly with data size. 10x data should result in ~10x time, not 50x time.

4. **Pragmatic, Not Perfect**: Thresholds balance strictness with practicality. Overly strict thresholds create flaky tests; overly lenient thresholds miss regressions.

5. **Regression Detection**: Primary goal is detecting performance regressions, not achieving theoretical optimal performance.

### Why Fixed Thresholds?

Fixed thresholds (e.g., < 1ms, < 10ms) are used because:

1. **Clarity**: Developers immediately understand performance expectations
2. **Consistency**: Same thresholds across all environments (with multipliers)
3. **Regression Detection**: Clear signal when performance degrades
4. **Realistic Expectations**: Based on measured production performance

**Trade-off**: Fixed thresholds may need adjustment as hardware evolves, but this happens infrequently (yearly, not weekly).

---

## Environment Considerations

### CI Environment Characteristics

**GitHub Actions Runners** (Standard configuration):
- **CPU**: 2-core shared virtualized CPU (variable performance)
- **Memory**: 7GB RAM
- **Disk**: SSD, shared I/O
- **Load**: Variable based on GitHub runner pool utilization
- **Timing Variance**: ±30-50% due to noisy neighbors

**Impact on Thresholds**:
- CI thresholds are typically 1.5-3x more lenient than local thresholds
- Parallel test execution (20 splits) increases variance further
- Resource contention causes occasional spikes (handled by retries)

### Local Development Characteristics

**Typical Developer Machines**:
- **CPU**: 4-16 core dedicated CPU (consistent performance)
- **Memory**: 16-64GB RAM
- **Disk**: NVMe SSD, dedicated I/O
- **Load**: Lower variance, predictable
- **Timing Variance**: ±5-15% under normal conditions

**Impact on Thresholds**:
- Local runs typically exceed performance expectations
- Useful for optimization work and profiling
- Developers can run benchmarks with stricter thresholds locally

### Environment Variable Configuration

Performance thresholds can be adjusted via environment variables:

```bash
# Use stricter thresholds (local development)
export ONEX_PERF_STRICTNESS=strict

# Use lenient thresholds (CI/CD)
export ONEX_PERF_STRICTNESS=ci

# Use default balanced thresholds
unset ONEX_PERF_STRICTNESS  # or export ONEX_PERF_STRICTNESS=default
```

---

## Threshold Categories

### 1. Model Creation Thresholds

**Operation**: Instantiating Pydantic models with validation

**Base Thresholds**:
| Data Size | Local (Strict) | Default | CI (Lenient) | Rationale |
|-----------|---------------|---------|--------------|-----------|
| 10 items | < 0.5ms | < 1ms | < 2ms | Small payloads are fast |
| 100 items | < 1ms | < 2ms | < 4ms | Medium payloads scale linearly |
| 1,000 items | < 5ms | < 10ms | < 20ms | Large payloads, Pydantic validation overhead |
| 10,000 items | < 25ms | < 50ms | < 100ms | Extra-large payloads, GC may trigger |

**Why These Values?**:
- **UUID Generation**: Each envelope/model requires 1-3 UUIDs (~10-30µs each)
- **Pydantic Validation**: Field validation adds ~0.01-0.1ms per field
- **Nested Structures**: Dict with lists requires recursive validation
- **Memory Allocation**: Large payloads trigger Python memory allocator overhead

**Real-World Context**: Model creation happens on every reducer operation. At 1,000 operations/second, 10ms per creation = 10 seconds/1000 operations = 1% CPU overhead (acceptable).

### 2. Serialization Thresholds

**Operation**: Converting models to dict (`model_dump()`) or JSON (`model_dump_json()`)

**Base Thresholds**:
| Data Size | Local (Strict) | Default | CI (Lenient) | Rationale |
|-----------|---------------|---------|--------------|-----------|
| 10 items | < 2.5ms | < 5ms | < 10ms | JSON encoding overhead |
| 100 items | < 5ms | < 10ms | < 20ms | Typical event bus payload |
| 1,000 items | < 25ms | < 50ms | < 100ms | Large message batching |
| 10,000 items | < 100ms | < 200ms | < 400ms | Bulk operations, compression recommended |

**Why These Values?**:
- **JSON Encoding**: Python's `json.dumps()` adds ~2-5ms overhead vs `model_dump()`
- **UUID Serialization**: Converting UUID objects to strings (~1µs per UUID)
- **DateTime Serialization**: ISO 8601 formatting (~5-10µs per timestamp)
- **Nested Structure Traversal**: Recursive dict/list serialization

**Real-World Context**: Serialization happens when publishing to event bus (Kafka/Redpanda). At 200ms for 10,000 items, throughput = 50,000 items/second (acceptable for batch operations).

### 3. Deserialization Thresholds

**Operation**: Reconstructing models from dict or JSON

**Base Thresholds**: Same as serialization (symmetric operation)

**Why These Values?**:
- **Validation Overhead**: Pydantic re-validates all fields during deserialization
- **Type Coercion**: Converting JSON strings back to Python types (UUID, datetime)
- **Object Construction**: Allocating memory for new model instances

**Real-World Context**: Deserialization happens when consuming events from event bus. Latency impacts end-to-end event processing time.

### 4. Field Validation Thresholds

**Operation**: Pydantic field validators (sentinel values, range checks)

**Base Thresholds**:
| Validation Type | Local (Strict) | Default | CI (Lenient) | Rationale |
|-----------------|---------------|---------|--------------|-----------|
| Per-field validation | < 0.05ms | < 0.1ms | < 0.2ms | Individual field validation |
| Sentinel validation overhead | < 0.1ms | < 0.2ms | < 0.4ms | Additional overhead for -1 checks |

**Why These Values?**:
- **Conditional Logic**: Sentinel validation adds if/else branches (~10-20ns)
- **Validator Call Overhead**: Pydantic validator decorators add ~100-500ns
- **Type Checking**: isinstance checks are fast (~10-50ns) but accumulate

**Real-World Context**: Field validation runs on every model creation. At 0.1ms per field with 10 fields = 1ms total (acceptable overhead).

### 5. Memory Usage Thresholds

**Operation**: RSS (Resident Set Size) memory increase

**Base Thresholds**:
| Data Size | Max Memory (10 instances) | Rationale |
|-----------|---------------------------|-----------|
| 10 items | < 1MB | Small payloads, minimal memory |
| 100 items | < 5MB | Medium payloads, ~50KB per instance |
| 1,000 items | < 20MB | Large payloads, ~2MB per instance |
| 10,000 items | < 100MB | Extra-large payloads, ~10MB per instance |

**Why These Values?**:
- **Python Object Overhead**: Each Python object has ~28-56 bytes overhead
- **UUID Storage**: Each UUID is 16 bytes + Python object wrapper (~56 bytes total)
- **Dict Storage**: Python dicts use hash tables (overhead ~30-70% of data size)
- **String Interning**: Short strings may be interned, reducing memory

**Environment Impact**:
- **Memory measurements are approximate**: RSS includes shared libraries, Python runtime overhead
- **GC Timing**: Garbage collector may not run immediately, affecting measurements
- **System State**: Other processes affect available memory

**Note**: Memory thresholds are **NOT configurable** via environment variables because memory usage is more consistent across environments than timing.

### 6. Bulk Operation Thresholds

**Operation**: Creating/serializing many objects in a loop

**Base Thresholds**:
| Operation | Count | Local (Strict) | Default | CI (Lenient) | Rationale |
|-----------|-------|---------------|---------|--------------|-----------|
| Bulk creation | 100 | < 80% | < 160% | < 320% | Overhead from UUID generation |
| Bulk creation | 1,000 | < 80% | < 160% | < 320% | Linear scaling expected |
| Bulk creation | 10,000 | < 100% | < 200% | < 350% | GC triggers, cache effects |
| Bulk serialization | 1,000 | < ±40% | < ±60% | < ±80% | Caching benefits allowed |

**Why Percentage-Based?**:
- Bulk operations measure **overhead** of adding fields (e.g., `source_node_id`)
- Percentage overhead isolates the impact of specific changes
- Allows negative overhead (caching benefits)

**Why These Values?**:
- **UUID Generation Dominates**: Adding 1 UUID (3 total vs 2) = ~50% more UUID calls
- **Cache Effects**: CPU cache warming can reduce overhead (explains negative overhead)
- **GC Timing**: Garbage collector may trigger at different times, affecting variance
- **Resource Contention**: CI runners share resources, increasing variance at scale

**CI Variance Explanation**:
- n=100: Low variance, minimal resource contention → 160% threshold sufficient
- n=1,000: Moderate variance, some GC interference → 200% threshold sufficient
- n=10,000: High variance, GC triggers, scheduler noise → 350% threshold required

**Historical Evolution**:
- **Initial**: 55% overhead (unrealistic for adding extra UUID)
- **Relaxed to 165%**: Based on measured 120-155% overhead
- **Relaxed to 200%**: CI variance showed 177-281% in parallel execution
- **Relaxed to 350% (n=10,000)**: CI split 6 measured 307% under resource pressure
- **Local Dev**: Typically 100-110% overhead (stable, predictable)

---

## Configuration via Environment Variables

### Implementation Pattern

**Current Status**: ❌ Not yet implemented (planned enhancement)

**Proposed Implementation**:

```python
# tests/performance/conftest.py (NEW FILE)
import os
from typing import Literal

def get_threshold_multiplier() -> float:
    """Get performance threshold multiplier based on environment.

    Returns:
        - 0.5 for "strict" (local development optimization)
        - 1.0 for "default" (balanced)
        - 2.0 for "ci" (lenient for CI runners)
    """
    strictness = os.getenv("ONEX_PERF_STRICTNESS", "default").lower()

    if strictness == "strict":
        return 0.5
    elif strictness == "ci":
        return 2.0
    else:
        return 1.0

# Global fixture for all performance tests
import pytest

@pytest.fixture(scope="session")
def threshold_multiplier() -> float:
    """Fixture providing threshold multiplier for all performance tests."""
    return get_threshold_multiplier()
```

**Usage in Tests**:

```python
# Before (fixed threshold)
def test_model_creation_performance(self, data_size: int, max_time_ms: float) -> None:
    assert avg_time_ms < max_time_ms, (
        f"Model creation took {avg_time_ms:.2f}ms, expected < {max_time_ms}ms"
    )

# After (configurable threshold)
def test_model_creation_performance(
    self, data_size: int, max_time_ms: float, threshold_multiplier: float
) -> None:
    adjusted_threshold = max_time_ms * threshold_multiplier
    assert avg_time_ms < adjusted_threshold, (
        f"Model creation took {avg_time_ms:.2f}ms, expected < {adjusted_threshold}ms "
        f"(base: {max_time_ms}ms, multiplier: {threshold_multiplier}x)"
    )
```

### Environment Variable Reference

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `ONEX_PERF_STRICTNESS` | `strict`, `default`, `ci` | `default` | Threshold strictness level |
| `CI` | `true`, `false` | `false` | Auto-detected by CI runners (GitHub Actions sets this) |

**Auto-Detection** (Recommended):

```python
def get_threshold_multiplier() -> float:
    # Auto-detect CI environment
    if os.getenv("CI") == "true":
        return 2.0  # Lenient for CI

    # Allow manual override
    strictness = os.getenv("ONEX_PERF_STRICTNESS", "default").lower()
    if strictness == "strict":
        return 0.5
    else:
        return 1.0  # Default for local
```

---

## Adjusting Thresholds

### When to Adjust Thresholds

✅ **Good Reasons to Adjust**:
1. **Hardware Upgrade**: CI runners upgraded from 2-core to 4-core
2. **Pydantic Version Change**: Pydantic 2.0 → 3.0 with performance improvements
3. **Python Version Change**: Python 3.12 → 3.13 with faster startup
4. **Consistent CI Failures**: 90%+ of CI runs exceed threshold (not a regression)
5. **Historical Data**: Multiple months of data show threshold is unrealistic

❌ **Bad Reasons to Adjust**:
1. **Single Test Failure**: One-off failures due to noisy neighbor (use retry instead)
2. **Optimization Avoidance**: Adjusting threshold to avoid fixing slow code
3. **Impatience**: Test takes too long, so increase timeout instead of optimizing
4. **Guesswork**: No data-driven analysis, just increasing threshold arbitrarily

### Adjustment Process

**Step 1: Gather Data**

```bash
# Run benchmarks locally 10 times
for i in {1..10}; do
    poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py \
        -k "test_model_creation_performance" -v -s | tee benchmark_$i.log
done

# Extract timing data
grep "avg:" benchmark_*.log | awk '{print $NF}' | sort -n
```

**Step 2: Calculate Statistics**

```python
import statistics

# Example timings (ms)
timings = [0.85, 0.92, 0.88, 0.91, 0.87, 0.89, 0.93, 0.86, 0.90, 0.88]

mean = statistics.mean(timings)
stdev = statistics.stdev(timings)
p95 = statistics.quantiles(timings, n=20)[18]  # 95th percentile

print(f"Mean: {mean:.2f}ms")
print(f"StdDev: {stdev:.2f}ms")
print(f"P95: {p95:.2f}ms")

# Recommended threshold: P95 + 2*StdDev
recommended = p95 + (2 * stdev)
print(f"Recommended threshold: {recommended:.2f}ms")
```

**Step 3: Document Change**

Update the following locations:

1. **Test docstring**: Update baseline in test method docstring
2. **Test parametrize**: Update `max_time_ms` value in `@pytest.mark.parametrize`
3. **This document**: Update threshold table in relevant section
4. **CHANGELOG.md**: Add entry explaining the change
5. **Git commit**: Use conventional commit format

**Example Commit Message**:

```
perf(benchmarks): adjust model creation threshold for 1000 items

Increase threshold from 10ms to 15ms based on 30-day CI performance data.
Analysis shows P95 latency = 12.8ms with stddev = 1.2ms across 450 CI runs.

New threshold = P95 + 2*stddev = 12.8 + 2.4 = 15.2ms (rounded to 15ms).

This change prevents flaky test failures while maintaining regression detection.
No performance regression detected - this reflects CI runner variance.

Data:
- Local dev (M2 MacBook): 6.2ms avg (no change needed)
- GitHub Actions (2-core): 12.8ms P95 (threshold update needed)
- Correlation ID: 95cac850-05a3-43e2-9e57-ccbbef683f43

Related: OMN-594
```

### Threshold Review Cadence

**Quarterly Review** (Every 3 months):
- Review all performance benchmarks for flakiness
- Analyze CI failure rates (>5% flakiness = threshold issue)
- Check for environment changes (GitHub runner updates)

**On-Demand Review** (Triggered by):
- Major dependency upgrade (Pydantic, FastAPI)
- Python version upgrade
- CI infrastructure changes
- Persistent test flakiness (>10% failure rate)

---

## CI Performance Degradation

### Detecting Degradation

**Signs of Performance Regression**:
1. **Gradual Trend**: Performance slowly degrades over multiple PRs
2. **Sudden Jump**: Single commit causes 2x performance hit
3. **Increased Variance**: Same test shows 50ms, then 200ms, then 80ms
4. **Timeout Failures**: Tests start hitting 60s timeout

**Distinguishing Regression from Variance**:

| Symptom | Regression | Variance | Action |
|---------|------------|----------|--------|
| Consistent slow | ✅ | ❌ | Investigate code |
| Sporadic slow | ❌ | ✅ | Adjust threshold |
| All tests slow | ✅ | ❌ | Check dependencies |
| One test slow | ❌ | ✅ | Check test isolation |

### Investigation Workflow

**Step 1: Reproduce Locally**

```bash
# Run benchmark locally
poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py \
    -k "test_model_creation_performance" -v -s --durations=10

# If fast locally but slow in CI → environment issue
# If slow both places → code regression
```

**Step 2: Profile the Slow Test**

```bash
# Profile with cProfile
poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py \
    -k "test_model_creation_performance" -v -s \
    --profile --profile-svg

# Analyze hotspots in profile.svg
```

**Step 3: Git Bisect for Regression**

```bash
# Find the commit that introduced the regression
git bisect start
git bisect bad HEAD  # Current commit is slow
git bisect good v0.3.6  # Known good commit

# Git will checkout commits for testing
poetry run pytest tests/performance/ -k "test_model_creation_performance" -x

# Mark each commit as good or bad
git bisect good  # or git bisect bad
```

**Step 4: Fix or Adjust**

**If Code Regression**:
- Revert problematic commit
- Optimize hot path identified by profiler
- Add inline comments explaining optimization

**If Environment Change**:
- Adjust thresholds following [Adjustment Process](#adjustment-process)
- Document environment change in commit message

### Handling Flaky Tests

**Retry Strategy** (Recommended):

```python
# conftest.py
import pytest

@pytest.fixture(autouse=True)
def retry_performance_tests(request):
    """Automatically retry performance tests 2 times on failure."""
    if "performance" in request.keywords:
        request.config.option.maxfail = 3  # Allow 2 retries
```

**Alternatively**, use `pytest-rerunfailures`:

```bash
poetry add --group dev pytest-rerunfailures

# Run with automatic retries
poetry run pytest tests/performance/ -v --reruns 2 --reruns-delay 1
```

---

## Historical Context

### Threshold Evolution

**v0.3.6 - Initial Benchmarks** (2025-12-16):
- Fixed thresholds based on local development (M2 MacBook)
- No environment-specific adjustments
- Frequent flakiness in CI (20-30% failure rate)

**v0.4.0 - CI-Aware Thresholds** (Planned):
- Environment variable configuration (`ONEX_PERF_STRICTNESS`)
- Auto-detection of CI environment
- Threshold multipliers (0.5x, 1x, 2x)
- Expected flakiness reduction to <5%

### Case Studies

#### Case Study 1: Bulk Creation Threshold Evolution

**Problem**: `test_bulk_creation_performance` flaky in CI for n=10,000

**Analysis**:
- Local dev: 100-110% overhead (consistent)
- CI early runs: 120-155% overhead
- CI under load: 177-281% overhead
- CI split 6: 307% overhead (resource contention)

**Resolution**:
- Initial threshold: 55% (unrealistic)
- First adjustment: 165% (based on 120-155% data)
- Second adjustment: 200% (based on 177-281% data)
- Third adjustment: 350% (based on 307% outlier + margin)

**Lesson**: Large-scale operations (n=10,000) amplify CI variance. Use more lenient thresholds for bulk operations.

#### Case Study 2: Sentinel Validation Overhead

**Problem**: Negative overhead observed (faster with extra validation)

**Analysis**:
- Expected: Additional if/else branch = small overhead
- Observed: -0.05ms to +0.15ms (includes negative values)
- Cause: CPU cache warming, branch prediction, random variance

**Resolution**:
- Use **absolute value** for threshold: `abs(overhead_pct) < 0.2`
- Allow negative overhead (caching benefits)
- Document that negative overhead is expected

**Lesson**: Micro-benchmarks (<0.1ms) are subject to measurement noise. Use statistical significance tests or larger sample sizes.

---

## Best Practices

### Writing New Benchmarks

✅ **Do**:
1. Use `time.perf_counter()` for high-resolution timing
2. Run multiple iterations (50-100) and report mean
3. Include warmup iterations (5-10) to prime caches
4. Document rationale for threshold in docstring
5. Use `@pytest.mark.parametrize` for data size variations
6. Add inline comments explaining threshold choice

❌ **Don't**:
1. Use `time.time()` (low resolution, subject to clock adjustments)
2. Run single iteration (too much variance)
3. Skip warmup (first run is always slower)
4. Use arbitrary thresholds without measurement
5. Mix multiple operations in one test (hard to debug)

### Threshold Selection

**Step 1: Measure Baseline**

```bash
# Run locally 10 times
for i in {1..10}; do
    poetry run pytest tests/performance/test_new_benchmark.py -v -s
done
```

**Step 2: Calculate P95 + 2*StdDev**

```python
import statistics
timings = [...]  # Your measurements
p95 = statistics.quantiles(timings, n=20)[18]
stdev = statistics.stdev(timings)
threshold = p95 + (2 * stdev)
```

**Step 3: Apply CI Multiplier**

```python
# For local dev
local_threshold = threshold

# For CI (default)
ci_threshold = threshold * 2.0

# For strict (local optimization)
strict_threshold = threshold * 0.5
```

**Step 4: Document**

```python
def test_new_benchmark(self, threshold_multiplier: float):
    """Test new feature performance.

    Performance Baseline:
        - Local dev (M2 MacBook): 5.2ms avg
        - CI (GitHub Actions 2-core): 11.8ms P95
        - Threshold: 15ms (P95 + 2*StdDev with 2x CI multiplier)

    Rationale:
        - UUID generation: 3 UUIDs × 10µs = 30µs
        - Pydantic validation: 5 fields × 100µs = 500µs
        - Nested structure: ~4ms for 100-item list
        - Measurement variance: ±2ms
    """
    max_time_ms = 15.0 * threshold_multiplier
    # ... test implementation
```

---

## Related Documentation

- [Model Reducer Output Benchmarks](./MODEL_REDUCER_OUTPUT_BENCHMARKS.md)
- [Source Node ID Benchmarks](./SOURCE_NODE_ID_BENCHMARKS.md)
- [CI Monitoring Guide](../ci/CI_MONITORING_GUIDE.md)
- [Parallel Testing Guide](../testing/PARALLEL_TESTING.md)

---

## Maintenance

**Quarterly Review Checklist**:
- [ ] Review all performance test flakiness (target: <5% failure rate)
- [ ] Analyze CI runner performance trends
- [ ] Check for Pydantic/Python version updates
- [ ] Update thresholds based on 3-month historical data
- [ ] Document any threshold adjustments in CHANGELOG.md

**On-Demand Review Triggers**:
- [ ] Performance test flakiness >10% for any single test
- [ ] GitHub Actions runner infrastructure changes
- [ ] Major dependency upgrade (Pydantic 2.x → 3.x)
- [ ] Python version upgrade (3.12 → 3.13)

---

**Last Updated**: 2025-12-16
**Status**: Active - Thresholds reviewed quarterly
**Next Review**: 2025-03-16
**Contact**: @omnibase_core-maintainers

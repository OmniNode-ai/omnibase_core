# Performance Benchmark CI Integration Guide

**Purpose**: Comprehensive guide for integrating performance benchmarks into CI pipeline with threshold enforcement and regression detection

**Last Updated**: 2025-12-16

**Related Documents**:
- [Performance Benchmark Thresholds](../performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md)
- [CI Monitoring Guide](./CI_MONITORING_GUIDE.md)
- [Model Reducer Output Benchmarks](../performance/MODEL_REDUCER_OUTPUT_BENCHMARKS.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Current CI Integration Status](#current-ci-integration-status)
3. [Running Benchmarks in CI](#running-benchmarks-in-ci)
4. [Threshold Enforcement Strategy](#threshold-enforcement-strategy)
5. [Failure Handling](#failure-handling)
6. [Performance Tracking Over Time](#performance-tracking-over-time)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Future Enhancements](#future-enhancements)

---

## Overview

### Purpose

Performance benchmarks ensure that code changes do not introduce performance regressions. This guide documents how benchmarks integrate with the CI pipeline, how to enforce thresholds, and how to handle failures.

### Goals

1. **Regression Detection**: Catch performance degradation before merge
2. **Consistent Baselines**: Maintain stable performance baselines across environments
3. **Fast Feedback**: Provide quick feedback on performance impact
4. **Historical Tracking**: Track performance trends over time

### Non-Goals

- ❌ **Absolute Performance Optimization**: Benchmarks detect regressions, not optimize code
- ❌ **Real-Time Production Monitoring**: CI benchmarks complement, not replace, APM tools
- ❌ **Competitive Benchmarking**: Focus is internal consistency, not external comparisons

---

## Current CI Integration Status

### Test Suite Organization

```text
tests/
├── unit/                          # Unit tests (12,000+ tests)
├── integration/                   # Integration tests
└── performance/                   # Performance benchmarks
    ├── test_model_reducer_output_benchmarks.py  ✅ 36 benchmarks
    ├── test_source_node_id_overhead.py          ✅ 12 benchmarks
    ├── contracts/
    │   ├── test_model_dependency_performance.py ✅ 8 benchmarks
    │   └── test_model_workflow_dependency_performance.py ✅ Active
    └── test_model_timeout_performance.py        ✅ Active
```

### CI Configuration

**Current Configuration** (.github/workflows/test.yml):

```yaml
# Performance benchmarks run as part of test-parallel job
test-parallel:
  strategy:
    matrix:
      split: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

  steps:
    - name: Run test split ${{ matrix.split }}/20
      run: |
        poetry run pytest tests/ \
          --splits 20 \
          --group ${{ matrix.split }} \
          -n auto \
          --timeout=60 \
          --timeout-method=thread \
          --tb=short \
          --junitxml=junit-${{ matrix.split }}.xml
```

**Status**: Performance benchmarks currently run **implicitly** as part of the full test suite across all 20 splits.

### Pytest Markers

**Configuration** (tests/pytest.ini):

```ini
markers =
    performance: marks tests as performance tests
    slow: marks tests as slow (deselect with '-m "not slow"')
```

**Usage in Benchmarks**:

```python
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(120)
class TestModelReducerOutputPerformance:
    """Performance benchmarks with extended timeout."""
```

**Key Markers**:
- `@pytest.mark.performance` - Identifies performance tests (can be selected with `-m performance`)
- `@pytest.mark.slow` - Indicates longer-running tests (can be excluded with `-m "not slow"`)
- `@pytest.mark.timeout(120)` - Extends timeout to 120 seconds for performance measurements

---

## Running Benchmarks in CI

### Method 1: Implicit Execution (Current)

**Status**: ✅ Active

**How it works**: Performance benchmarks run as part of the full test suite across all 20 parallel splits.

**Pros**:
- ✅ Zero additional CI job overhead
- ✅ Benchmarks always run on every PR/push
- ✅ No separate configuration needed

**Cons**:
- ⚠️ Performance results mixed with unit test output
- ⚠️ Harder to track performance-specific failures
- ⚠️ No dedicated performance reporting

**Example**: Performance tests distributed across splits like any other test.

### Method 2: Explicit Dedicated Job (Recommended Enhancement)

**Status**: ⚠️ Proposed (not yet implemented)

**Configuration**:

```yaml
# Add to .github/workflows/test.yml after test-parallel job
performance-benchmarks:
  name: Performance Benchmarks
  needs: [lint, pyright, exports-validation]  # Phase 1 dependencies
  runs-on: ubuntu-latest
  timeout-minutes: 15

  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'

    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: ${{ env.POETRY_VERSION }}
        virtualenvs-create: true
        virtualenvs-in-project: true

    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v4
      with:
        path: .venv
        key: >-
          venv-${{ runner.os }}-${{ env.PYTHON_VERSION }}-
          ${{ hashFiles('**/poetry.lock') }}-
          ${{ env.CACHE_VERSION }}

    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      run: poetry install --no-interaction --no-root

    - name: Install project
      run: poetry install --no-interaction

    - name: Run performance benchmarks
      run: |
        poetry run pytest tests/performance/ \
          -m performance \
          -v \
          --tb=short \
          --durations=10 \
          --junitxml=junit-performance.xml
      continue-on-error: false  # Fail CI on performance regression

    - name: Upload performance results
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: performance-results
        path: junit-performance.xml
        retention-days: 30

    - name: Performance summary
      if: always()
      run: |
        echo "## Performance Benchmark Results" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "See job logs for detailed timing breakdown." >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "**Slowest 10 tests**: Check 'Run performance benchmarks' step output" >> $GITHUB_STEP_SUMMARY
```

**Pros**:
- ✅ Dedicated performance visibility
- ✅ Separate performance failure reporting
- ✅ Performance-specific timeout (15 min vs 30 min for full suite)
- ✅ Dedicated artifact upload for historical tracking

**Cons**:
- ⚠️ Additional CI job (adds ~5-10 minutes to total pipeline)
- ⚠️ Requires updating test-summary job to include performance-benchmarks dependency

### Method 3: On-Demand Execution (Optional)

**Status**: ⚠️ Optional enhancement

**Use Case**: Run benchmarks only when performance-critical files change

**Configuration**:

```yaml
performance-benchmarks:
  name: Performance Benchmarks
  needs: [lint, pyright, exports-validation]
  runs-on: ubuntu-latest
  timeout-minutes: 15

  # Only run if performance-related files changed
  if: |
    github.event_name == 'workflow_dispatch' ||
    contains(github.event.head_commit.message, '[benchmark]') ||
    contains(github.event.pull_request.labels.*.name, 'performance')

  steps:
    # ... same as Method 2
```

**Trigger Methods**:
1. **Manual**: `workflow_dispatch` button in GitHub Actions UI
2. **Commit Message**: Include `[benchmark]` in commit message
3. **PR Label**: Add `performance` label to PR

**Pros**:
- ✅ Reduces CI load for non-performance changes
- ✅ Still available on-demand when needed

**Cons**:
- ⚠️ May miss subtle regressions in non-performance PRs
- ⚠️ Relies on developer discipline to trigger

---

## Threshold Enforcement Strategy

### Current Enforcement Mechanism

**Implementation**: Thresholds are **hardcoded in test assertions**

**Example** (from test_model_reducer_output_benchmarks.py):

```python
@pytest.mark.parametrize(
    ("data_size", "max_time_ms"),
    [
        pytest.param(10, 1.0, id="small_10_items"),      # < 1ms
        pytest.param(100, 2.0, id="medium_100_items"),   # < 2ms
        pytest.param(1000, 10.0, id="large_1000_items"), # < 10ms
        pytest.param(10000, 50.0, id="xlarge_10000_items"), # < 50ms
    ],
)
def test_model_creation_performance(
    self, data_size: int, max_time_ms: float
) -> None:
    """Benchmark model creation with varying data sizes."""
    # ... benchmark code ...

    avg_time_ms = avg_time * 1000
    assert avg_time_ms < max_time_ms, (
        f"Model creation for {data_size} items took {avg_time_ms:.2f}ms, "
        f"expected < {max_time_ms}ms (threshold exceeded by "
        f"{((avg_time_ms / max_time_ms) - 1) * 100:.1f}%)"
    )
```

**Pros**:
- ✅ Simple and explicit
- ✅ No external configuration needed
- ✅ Thresholds version-controlled with tests

**Cons**:
- ⚠️ No environment-specific adjustments (local vs CI)
- ⚠️ Changing thresholds requires code changes
- ⚠️ No central threshold registry

### Recommended Enhancement: Environment-Aware Thresholds

**Status**: ⚠️ Proposed (documented in PERFORMANCE_BENCHMARK_THRESHOLDS.md)

**Configuration** (tests/performance/conftest.py - NOT YET IMPLEMENTED):

```python
"""Performance test configuration and fixtures."""

import os
from typing import Literal

import pytest


def get_threshold_multiplier() -> float:
    """Get performance threshold multiplier based on environment.

    Returns:
        - 0.5 for "strict" (local development optimization)
        - 1.0 for "default" (balanced)
        - 2.0 for "ci" (lenient for CI runners)
    """
    # Auto-detect CI environment
    if os.getenv("CI") == "true":
        return 2.0  # Lenient for CI

    # Allow manual override
    strictness = os.getenv("ONEX_PERF_STRICTNESS", "default").lower()
    if strictness == "strict":
        return 0.5
    elif strictness == "ci":
        return 2.0
    else:
        return 1.0  # Default for local


@pytest.fixture(scope="session")
def threshold_multiplier() -> float:
    """Fixture providing threshold multiplier for all performance tests."""
    return get_threshold_multiplier()
```

**Updated Test Usage**:

```python
def test_model_creation_performance(
    self, data_size: int, max_time_ms: float, threshold_multiplier: float
) -> None:
    """Benchmark with environment-aware thresholds."""
    # ... benchmark code ...

    adjusted_threshold = max_time_ms * threshold_multiplier
    assert avg_time_ms < adjusted_threshold, (
        f"Model creation for {data_size} items took {avg_time_ms:.2f}ms, "
        f"expected < {adjusted_threshold}ms (base: {max_time_ms}ms, "
        f"multiplier: {threshold_multiplier}x)"
    )
```

**Benefits**:
- ✅ CI-aware thresholds (2x more lenient)
- ✅ Local strict mode for optimization work (0.5x)
- ✅ No code changes needed to adjust environment behavior

### Threshold Failure Modes

**Hard Failure** (Current Default):

```python
# Test assertion fails → CI job fails → PR blocked
assert avg_time_ms < max_time_ms
```

**Soft Failure with Warning** (Proposed Enhancement):

```python
# Test passes but logs warning → CI succeeds → Manual review needed
if avg_time_ms > max_time_ms:
    pytest.warn(
        UserWarning(
            f"Performance threshold exceeded: {avg_time_ms:.2f}ms > {max_time_ms}ms"
        )
    )
```

**Recommendation**: Use **hard failure** for critical paths, **soft failure** for informational benchmarks.

---

## Failure Handling

### When Benchmarks Fail in CI

**Failure Symptoms**:
1. ❌ Test assertion failure in performance test
2. ❌ CI job marked as failed
3. ❌ PR blocked from merging (if branch protection enabled)

**Example Failure Output**:

```text
FAILED tests/performance/test_model_reducer_output_benchmarks.py::TestModelReducerOutputPerformance::test_model_creation_performance[large_1000_items]

AssertionError: Model creation for 1000 items took 15.32ms, expected < 10ms (threshold exceeded by 53.2%)
```

### Investigation Workflow

**Step 1: Determine Failure Type**

| Failure Pattern | Type | Action |
|----------------|------|--------|
| Single split fails | Flaky test | Retry, investigate if repeats |
| All splits fail | Real regression | Investigate code changes |
| Sporadic failures | Environment variance | Adjust thresholds |
| Gradual degradation | Accumulating overhead | Optimize or adjust |

**Step 2: Reproduce Locally**

```bash
# Run the specific failing benchmark
poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py \
  -k "test_model_creation_performance[large_1000_items]" \
  -v -s

# If fast locally but slow in CI → environment issue
# If slow both places → code regression
```

**Step 3: Profile the Regression**

```bash
# Profile with cProfile
poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py \
  -k "test_model_creation_performance" \
  -v -s \
  --profile \
  --profile-svg

# Analyze profile.svg for hotspots
```

**Step 4: Root Cause Analysis**

**Code Regression**:
```bash
# Use git bisect to find the offending commit
git bisect start
git bisect bad HEAD  # Current commit is slow
git bisect good v0.3.6  # Known good commit

# Git will checkout commits for testing
poetry run pytest tests/performance/ -k "test_model_creation_performance" -x

# Mark each commit as good or bad
git bisect good  # or git bisect bad
```

**Environment Change**:
- Check GitHub Actions runner updates
- Check for Pydantic version changes (poetry.lock diff)
- Compare CI logs across multiple runs for consistency

**Step 5: Resolution**

**Option A: Fix Code Regression**
```bash
# Revert problematic commit or optimize hot path
git revert <commit-sha>

# Or optimize the identified bottleneck
# ... code changes ...

# Re-run benchmarks to verify fix
poetry run pytest tests/performance/ -v
```

**Option B: Adjust Threshold (If Justified)**

**Criteria for threshold adjustment**:
- ✅ Environment upgrade (e.g., GitHub runner hardware change)
- ✅ Dependency upgrade with known performance impact (e.g., Pydantic 2.11 → 2.12)
- ✅ Consistent failure across 10+ CI runs (not a one-off)
- ✅ Historical data supports new threshold (P95 + 2*StdDev)

**Adjustment process**:
```python
# 1. Update threshold in test parametrize
pytest.param(1000, 15.0, id="large_1000_items"),  # Was 10.0ms

# 2. Document in commit message
"""
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
"""
```

### Handling Flaky Benchmarks

**Symptoms**:
- ✅ Test passes 80% of the time
- ✅ Failures are non-deterministic
- ✅ Same code produces different results across runs

**Solution 1: Increase Threshold Margin**

```python
# Add safety margin to threshold
pytest.param(1000, 15.0, id="large_1000_items"),  # Was 10ms (50% margin)
```

**Solution 2: Use Statistical Significance**

```python
# Run benchmark multiple times and use P95
def test_model_creation_performance(self, data_size: int, max_time_ms: float) -> None:
    """Benchmark with statistical significance."""
    times = []
    for _ in range(10):  # Run 10 times
        avg_time = self.time_operation(...)
        times.append(avg_time * 1000)

    # Use 95th percentile instead of single measurement
    p95_time_ms = statistics.quantiles(times, n=20)[18]

    assert p95_time_ms < max_time_ms, (
        f"P95 time {p95_time_ms:.2f}ms exceeds threshold {max_time_ms}ms"
    )
```

**Solution 3: Retry Failed Benchmarks**

**Configuration** (pyproject.toml):

```toml
[tool.pytest.ini_options]
addopts = [
    "--reruns=2",  # Auto-retry failed tests twice
    "--reruns-delay=1",  # 1 second delay between reruns
]
```

**Note**: Already configured in pyproject.toml, so flaky benchmarks automatically retry.

---

## Performance Tracking Over Time

### Current Status

**Tracking Mechanism**: ❌ Not yet implemented

**Available Data**:
- JUnit XML artifacts (test pass/fail, but no timing details)
- GitHub Actions logs (manual extraction required)
- No historical trend database

### Recommended Enhancement: Performance History Tracking

**Option 1: GitHub Actions Artifacts (Simple)**

**Configuration**:

```yaml
# Add to .github/workflows/test.yml performance-benchmarks job
- name: Extract performance metrics
  if: always()
  run: |
    # Extract timing data from pytest output
    grep "passed in" pytest.log | tee performance-timing.txt

    # Generate performance report
    cat > performance-report.json <<EOF
    {
      "timestamp": "$(date -Iseconds)",
      "commit": "${{ github.sha }}",
      "branch": "${{ github.ref_name }}",
      "timings": $(grep "avg:" pytest.log | jq -R -s 'split("\n") | map(select(length > 0))')
    }
    EOF

- name: Upload performance report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: performance-report-${{ github.sha }}
    path: |
      performance-timing.txt
      performance-report.json
    retention-days: 90
```

**Pros**: Simple, no external dependencies
**Cons**: Manual analysis required, no automatic trend detection

**Option 2: GitHub Pages Performance Dashboard (Advanced)**

**Implementation**:

```yaml
# New workflow: .github/workflows/performance-dashboard.yml
name: Performance Dashboard

on:
  workflow_run:
    workflows: ["Test Suite"]
    types: [completed]

jobs:
  update-dashboard:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout gh-pages branch
        uses: actions/checkout@v4
        with:
          ref: gh-pages

      - name: Download performance artifacts
        uses: actions/download-artifact@v4
        with:
          name: performance-report-${{ github.event.workflow_run.head_sha }}
          path: data/

      - name: Update dashboard
        run: |
          # Append new data to historical JSON
          cat data/performance-report.json >> performance-history.json

          # Generate HTML dashboard with charts
          python scripts/generate-performance-dashboard.py

      - name: Commit and push
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .
          git commit -m "Update performance dashboard"
          git push
```

**Pros**: Visual trend analysis, automatic updates, historical tracking
**Cons**: Requires initial setup, maintenance overhead

**Option 3: External APM Tool (Production-Grade)**

**Tools**:
- DataDog CI Visibility
- New Relic Synthetic Monitoring
- Grafana + InfluxDB

**Pros**: Professional monitoring, alerting, trend analysis
**Cons**: Additional cost, external dependency

**Recommendation**: Start with **Option 1** (artifacts), upgrade to **Option 2** (dashboard) if needed.

### Manual Performance Tracking

**Local Tracking Script** (scripts/track-performance.sh):

```bash
#!/usr/bin/env bash
# Track performance benchmarks over time

set -euo pipefail

RESULTS_DIR="performance-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMMIT=$(git rev-parse --short HEAD)

mkdir -p "$RESULTS_DIR"

echo "Running performance benchmarks..."
poetry run pytest tests/performance/ \
  -m performance \
  -v \
  --tb=short \
  --durations=10 \
  | tee "$RESULTS_DIR/benchmark_${TIMESTAMP}_${COMMIT}.log"

echo "Results saved to $RESULTS_DIR/benchmark_${TIMESTAMP}_${COMMIT}.log"
echo ""
echo "To compare with previous runs:"
echo "  diff $RESULTS_DIR/benchmark_*.log"
```

**Usage**:

```bash
# Run benchmarks and save results
./scripts/track-performance.sh

# Compare two runs
diff performance-results/benchmark_20251216_*.log
```

---

## Best Practices

### 1. Benchmark Design

✅ **Do**:
- Use high-resolution timing (`time.perf_counter()`)
- Run multiple iterations and report mean (50-100 iterations)
- Include warmup iterations (5-10) to prime caches
- Document threshold rationale in docstrings
- Use `@pytest.mark.parametrize` for data size variations

❌ **Don't**:
- Use `time.time()` (low resolution, subject to clock adjustments)
- Run single iteration (too much variance)
- Skip warmup (first run is always slower)
- Use arbitrary thresholds without measurement
- Mix multiple operations in one test (hard to debug)

### 2. Threshold Selection

**Process**:
1. **Measure baseline locally** (10 runs minimum)
2. **Calculate P95 + 2*StdDev**
3. **Apply CI multiplier** (2x for GitHub Actions)
4. **Document rationale** in test docstring

**Example**:

```python
@pytest.mark.parametrize(
    ("data_size", "max_time_ms"),
    [
        # Threshold rationale:
        # - Local P95: 0.8ms, StdDev: 0.1ms
        # - Calculated: 0.8 + 2*0.1 = 1.0ms
        # - CI multiplier: 1.0 * 2 = 2.0ms (GitHub Actions variance)
        # - See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md
        pytest.param(10, 1.0, id="small_10_items"),
    ],
)
```

### 3. CI Configuration

✅ **Do**:
- Run benchmarks on every PR (regression detection)
- Use dedicated timeout for performance tests (120s)
- Upload artifacts for historical tracking
- Generate performance summary in GitHub Actions summary

❌ **Don't**:
- Skip benchmarks to save CI time (defeats purpose)
- Use same timeout as unit tests (benchmarks are slower)
- Ignore failures (investigate all regressions)

### 4. Failure Response

**When benchmark fails**:
1. ✅ **First**: Check if it's a real regression (reproduce locally)
2. ✅ **Second**: Profile to find bottleneck
3. ✅ **Third**: Fix code or adjust threshold (with justification)
4. ❌ **Never**: Blindly increase threshold without investigation

### 5. Documentation

**Required Documentation**:
- Test docstring with baseline and rationale
- Threshold table in PERFORMANCE_BENCHMARK_THRESHOLDS.md
- Commit message explaining threshold changes
- Performance report in PR description (if relevant)

**Example PR Description**:

```markdown
## Performance Impact

**Benchmarks Run**: ✅ All 36 performance tests passing

**Threshold Changes**: None

**Performance Metrics**:
- Model creation (1000 items): 8.2ms (baseline: < 10ms) ✅
- Serialization (1000 items): 42ms (baseline: < 50ms) ✅
- Memory usage (10,000 items): 85MB (baseline: < 100MB) ✅

**Analysis**: No performance regression detected. All benchmarks within expected thresholds.
```

---

## Troubleshooting

### Problem: Benchmarks Timeout in CI

**Symptoms**: `pytest-timeout` kills benchmark after 60s (default test timeout)

**Solution**: Use extended timeout for performance tests

```python
@pytest.mark.timeout(120)  # 120 seconds for performance tests
class TestModelReducerOutputPerformance:
    """Performance benchmarks with extended timeout."""
```

### Problem: Benchmarks Pass Locally but Fail in CI

**Cause**: CI runners are slower and more variable than local machines

**Solutions**:
1. **Environment-aware thresholds** (2x multiplier for CI)
2. **Increase threshold margin** (add 50-100% safety margin)
3. **Statistical significance** (use P95 instead of mean)

### Problem: Benchmarks Are Flaky

**Symptoms**: Same test passes/fails randomly across CI runs

**Solutions**:
1. **Automatic retries** (already configured: `--reruns=2`)
2. **Increase threshold** to account for variance
3. **Statistical testing** (run multiple iterations, use percentiles)

### Problem: Cannot Reproduce Failure Locally

**Cause**: Different hardware, Python version, or system load

**Debug Steps**:
```bash
# 1. Check Python version matches CI
python --version  # Should be 3.12

# 2. Check Poetry version matches CI
poetry --version  # Should be 2.2.1

# 3. Run in clean environment
poetry env remove python3.12
poetry install
poetry run pytest tests/performance/ -v

# 4. Simulate CI load (run in parallel)
poetry run pytest tests/performance/ -n auto -v
```

### Problem: Memory Benchmark Failures

**Symptoms**: Memory usage exceeds threshold

**Common Causes**:
- Python GC not running (memory not released)
- Background processes consuming memory
- Memory leak in test setup

**Solution**:

```python
import gc

def test_memory_usage(self) -> None:
    """Benchmark memory with explicit GC."""
    gc.collect()  # Force GC before measurement

    baseline_rss = psutil.Process().memory_info().rss

    # ... create models ...

    gc.collect()  # Force GC after creation

    after_rss = psutil.Process().memory_info().rss
    increase_mb = (after_rss - baseline_rss) / (1024 * 1024)

    assert increase_mb < threshold_mb
```

---

## Future Enhancements

### Phase 1: Dedicated CI Job (Priority: High)

**Status**: ⚠️ Proposed

**Timeline**: Q1 2025

**Deliverables**:
- Dedicated `performance-benchmarks` job in test.yml
- Separate artifact upload for performance results
- Performance summary in GitHub Actions summary

**Benefits**: Better visibility, separate failure reporting

### Phase 2: Environment-Aware Thresholds (Priority: High)

**Status**: ⚠️ Documented, not implemented

**Timeline**: Q1 2025

**Deliverables**:
- `tests/performance/conftest.py` with `threshold_multiplier` fixture
- Update all benchmarks to use multiplier
- CI auto-detection (`CI=true` → 2x thresholds)

**Benefits**: Reduce flakiness, maintain strict local thresholds

### Phase 3: Performance Dashboard (Priority: Medium)

**Status**: ⚠️ Proposed

**Timeline**: Q2 2025

**Deliverables**:
- GitHub Pages performance dashboard
- Historical trend charts (line graphs)
- Automatic regression detection (>10% degradation alerts)

**Benefits**: Visual trend analysis, proactive regression detection

### Phase 4: Statistical Significance Testing (Priority: Low)

**Status**: ⚠️ Research phase

**Timeline**: Q3 2025

**Deliverables**:
- Statistical significance tests (t-test, Mann-Whitney U)
- Confidence intervals for performance metrics
- Automated threshold recommendations

**Benefits**: More robust regression detection, fewer false positives

---

## Summary

### Current State

✅ **Working**:
- 36+ performance benchmarks across 4 test files
- Implicit execution in CI (part of test-parallel splits)
- Hardcoded thresholds with clear rationale
- Automatic retries for flaky tests (`--reruns=2`)

⚠️ **Needs Enhancement**:
- Environment-aware thresholds (local vs CI)
- Dedicated CI job for performance visibility
- Historical performance tracking
- Automated regression alerts

### Quick Reference

**Run benchmarks locally**:
```bash
poetry run pytest tests/performance/ -m performance -v
```

**Run specific benchmark**:
```bash
poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py \
  -k "test_model_creation_performance" -v
```

**Debug slow benchmark**:
```bash
poetry run pytest tests/performance/ -k "slow_test" -v -s --durations=10
```

**Adjust threshold (when justified)**:
1. Measure local baseline (10+ runs)
2. Calculate P95 + 2*StdDev
3. Apply CI multiplier (2x)
4. Update parametrize and document

**Report performance regression**:
1. Create GitHub issue with benchmark output
2. Include local vs CI comparison
3. Attach profiling results (if available)
4. Tag with `performance` label

---

**Last Updated**: 2025-12-16
**Related PR**: #205
**Status**: Active - enhancements planned for Q1 2025
**Contact**: @omnibase_core-maintainers

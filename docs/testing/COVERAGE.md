# Code Coverage Testing

This document explains the parallel coverage testing approach for Omnibase Core.

## ⚠️ Important: Resource Management

**CRITICAL**: The parallel coverage script is resource-constrained for local execution.

- **CI runs 12 splits on separate isolated runners** (horizontal scaling)
- **Local runs splits with concurrency limits on one machine** (vertical scaling with constraints)
- **Default configuration**: 3 concurrent splits × 4 workers = 12 total workers
- **See [PARALLEL_TESTING.md](PARALLEL_TESTING.md)** for detailed resource management and architecture

## Problem

Running coverage tests sequentially on the entire test suite is slow (~30+ minutes). CI uses 12 parallel splits for speed but doesn't collect coverage data. We need a local solution that combines both approaches: parallel execution for speed and coverage collection for quality metrics.

## Solution: Resource-Constrained Parallel Coverage

The `scripts/run-coverage-parallel.sh` script runs pytest with coverage collection across 12 splits using controlled batching and explicit worker limits, then combines the results into a unified coverage report.

### Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                  Parallel Test Execution                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Split 1  →  .coverage.1                                     │
│  Split 2  →  .coverage.2                                     │
│  Split 3  →  .coverage.3                                     │
│  ...                                                          │
│  Split 12 →  .coverage.12                                    │
│                                                               │
│              ↓ (parallel execution)                          │
│                                                               │
│              ✓ All splits complete                           │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                   Coverage Combination                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  coverage combine  →  .coverage                              │
│  coverage report   →  Terminal output                        │
│  coverage html     →  htmlcov/index.html                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Quick Start

```bash
# Run parallel coverage tests with default configuration (from project root)
# Default: 3 concurrent splits × 4 workers = 12 total workers
./scripts/run-coverage-parallel.sh
```

### Resource Configuration

Customize parallelism based on your machine's capabilities:

```bash
# Conservative (low-end machines: 4-6 cores, 8-16 GB RAM)
export MAX_CONCURRENT_SPLITS=2
export WORKERS_PER_SPLIT=3
./scripts/run-coverage-parallel.sh

# Balanced (mid-range machines: 8-10 cores, 16-32 GB RAM) - DEFAULT
export MAX_CONCURRENT_SPLITS=3
export WORKERS_PER_SPLIT=4
./scripts/run-coverage-parallel.sh

# Aggressive (high-end machines: 12+ cores, 32+ GB RAM)
export MAX_CONCURRENT_SPLITS=4
export WORKERS_PER_SPLIT=6
./scripts/run-coverage-parallel.sh
```

**See [PARALLEL_TESTING.md](PARALLEL_TESTING.md#resource-configuration-guide)** for detailed configuration guidance.

### Expected Output

```text
🧪 Running parallel coverage tests (12 splits)
📊 Resource Configuration:
   • Concurrent splits: 3
   • Workers per split: 4
   • Total concurrent workers: 12
   • Max failures before abort: 10

🧹 Cleaning previous coverage data...
🚀 Launching test splits (batches of 3)...
⏳ Waiting for remaining splits to complete...
[Split 1/12] Starting...
[Split 2/12] Starting...
[Split 3/12] Starting...
[Split 1/12] ✓ Complete
[Split 4/12] Starting...
...
[Split 12/12] ✓ Complete
✅ All splits complete in 5m 32s
🔗 Combining coverage data from all splits...
📊 Generating coverage reports...

Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
src/omnibase_core/__init__.py                 5      0   100%
src/omnibase_core/core/__init__.py           12      0   100%
...
-------------------------------------------------------------
TOTAL                                      8542    542    94%

✅ Coverage report complete!
📂 HTML report: htmlcov/index.html
🌐 Open with: open htmlcov/index.html
⏱️  Total time: 3m 42s
```

### Viewing HTML Report

```bash
# Open coverage report in browser
open htmlcov/index.html
```

The HTML report provides:
- Line-by-line coverage visualization
- Source code highlighting
- Drill-down navigation by module
- Missing coverage identification

## Performance Comparison

| Approach | Execution Time | Coverage Data | Resource Usage | Use Case |
|----------|---------------|---------------|----------------|----------|
| **Sequential** | ~30+ minutes | ✅ Yes | Low (10-20% CPU) | Baseline reference |
| **CI Parallel** | ~3-5 minutes | ✅ Yes (main only) | 12 isolated runners | Production CI |
| **Local Parallel (constrained)** | ~5-8 minutes | ✅ Yes | Moderate (60-80% CPU) | **Local development (recommended)** |
| **Local Parallel (unconstrained)** | ❌ System freeze | ❌ No | Critical (800%+ CPU thrashing) | ⚠️ Don't use |

**Note**: Local parallel is slower than CI parallel (5-8 min vs 3-5 min) because CI uses 12 separate machines while local uses resource constraints on one machine. This is an acceptable tradeoff for system stability.

**See [PARALLEL_TESTING.md](PARALLEL_TESTING.md#ci-vs-local-architectural-differences)** for detailed architecture comparison.

## Configuration

### Coverage Settings

Coverage configuration is defined in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/omnibase_core"]
branch = true
parallel = true
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
fail_under = 60
precision = 2
show_missing = true
skip_covered = false
```

### Split Configuration

The script uses 12 splits with resource constraints:
- **Splits**: 12 total (mirrors CI split count)
- **Concurrency**: Max 3 splits run simultaneously (default, configurable)
- **Workers per split**: 4 workers (explicit, not auto-detected)
- **Total workers**: 3 splits × 4 workers = 12 concurrent workers (safe for 8+ core machines)
- **Test distribution**: pytest-split ensures deterministic, balanced distribution (~916 tests per split)

**Key Difference from CI**:
- CI: 12 splits on 12 separate runners with `-n auto` each (isolated resources)
- Local: 12 splits batched (3 at a time) with `-n 4` each (shared resources, constrained)

## Technical Details

### Coverage File Management

1. **Pre-Execution Cleanup**: `rm -f .coverage .coverage.*`
   - Ensures clean slate for each run
   - Prevents stale coverage data corruption

2. **Parallel Execution**: `COVERAGE_FILE=.coverage.$i`
   - Each split writes to a unique coverage file
   - Prevents race conditions and data loss
   - Enables true parallel execution

3. **Combination**: `coverage combine`
   - Merges all `.coverage.N` files into `.coverage`
   - Resolves overlapping coverage data
   - Produces unified coverage database

### Error Handling

The script uses `set -e` to fail fast on errors:
- If any split fails, the script exits immediately
- Coverage combination only runs if all splits succeed
- Exit code propagates to caller (useful for CI integration)

## Troubleshooting

### Issue: "No data to combine"

**Cause**: All splits may have failed or not produced coverage data.

**Solution**:
```bash
# Check for coverage files
ls -la .coverage.*

# Run a single split manually to debug
COVERAGE_FILE=.coverage.test poetry run pytest tests/ \
  --splits 12 \
  --group 1 \
  --cov=src/omnibase_core \
  --cov-report=term \
  -v
```

### Issue: Coverage percentage is lower than expected

**Cause**: Some files may not be executed by any tests.

**Solution**:
```bash
# Identify uncovered files
poetry run coverage report --show-missing

# Check which tests cover specific files
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing
```

### Issue: Script hangs or doesn't complete

**Cause**: One or more splits may be stuck or resource exhaustion occurred.

**Solution**:
```bash
# Monitor running processes
ps aux | grep pytest

# Kill stuck processes
pkill -f "pytest tests/"

# Reduce resource usage
export MAX_CONCURRENT_SPLITS=2
export WORKERS_PER_SPLIT=2
./scripts/run-coverage-parallel.sh
```

**See [PARALLEL_TESTING.md](PARALLEL_TESTING.md#troubleshooting)** for comprehensive troubleshooting guide.

### Issue: System becomes unresponsive during test run

**Cause**: Too many concurrent workers causing resource exhaustion.

**Solution**:
```bash
# Reduce concurrency immediately
export MAX_CONCURRENT_SPLITS=2
export WORKERS_PER_SPLIT=3

# Run with resource monitoring
./scripts/run-coverage-parallel.sh

# The script will warn if configuration is too aggressive
```

### Issue: Resource warning displayed

**Example**:
```text
⚠️  WARNING: Total workers (16) exceeds 2× CPU cores (8)
```

**Action**: This is a warning, not an error. The script will run, but:
- If system becomes sluggish, reduce `MAX_CONCURRENT_SPLITS` or `WORKERS_PER_SPLIT`
- If system handles it fine, you can continue (but monitor resources)
- Follow the warning's recommendations if you experience any performance issues

## Integration with CI/CD

While this script is designed for local development, it can be integrated into CI:

```yaml
# .github/workflows/coverage.yml
- name: Run parallel coverage tests
  run: ./scripts/run-coverage-parallel.sh

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: .coverage
```

## Best Practices

1. **Run Before PRs**: Execute parallel coverage before creating pull requests
2. **Monitor Trends**: Track coverage percentage over time
3. **Target Uncovered Code**: Use HTML report to identify and test critical uncovered paths
4. **Balance Speed vs Depth**: Use parallel coverage for quick checks, sequential for comprehensive analysis
5. **Update Regularly**: Run coverage after significant codebase changes

## Related Documentation

- **[PARALLEL_TESTING.md](PARALLEL_TESTING.md)** - Detailed parallel testing architecture, resource management, and troubleshooting
- [TEST-SUITE-EVENT-LOOP-FIX-SUMMARY.md](TEST-SUITE-EVENT-LOOP-FIX-SUMMARY.md) - Event loop fixes in test suite
- Project root `CLAUDE.md` - Poetry usage requirements
- `.github/workflows/test.yml` - CI test configuration and matrix strategy
- `scripts/run-coverage-parallel.sh` - Parallel coverage script implementation

## Maintenance

### Adding New Test Splits

To increase parallelization (e.g., 24 splits):

```bash
# Edit scripts/run-coverage-parallel.sh
for i in {1..24}; do  # Changed from {1..12}
  ...
  --splits 24 \       # Changed from --splits 12
  --group $i \
  ...
done
```

### Adjusting Coverage Thresholds

```bash
# Edit pyproject.toml
[tool.coverage.report]
fail_under = 70  # Increased from 60
```

Then re-run the script to validate against new threshold.

## Performance Metrics

Based on typical runs with default configuration (3 concurrent splits × 4 workers):
- **Total Tests**: ~10,987 tests across 12 splits
- **Execution Time**: 5-8 minutes (vs 30+ sequential, vs 3-5 CI parallel)
- **Speedup Factor**: ~4-6x faster than sequential
- **Coverage Accuracy**: Identical to sequential runs
- **Resource Usage**: Moderate CPU (60-80%), moderate memory (~2-6 GB)
- **System Responsiveness**: Remains responsive for other tasks

**Configuration Impact**:
- Conservative (2 splits × 3 workers): 8-12 minutes, 40-60% CPU
- Balanced (3 splits × 4 workers): 5-8 minutes, 60-80% CPU (default)
- Aggressive (4 splits × 6 workers): 4-6 minutes, 90-100% CPU (high-end only)

## Conclusion

The resource-constrained parallel coverage approach provides the best balance for local development:
- **Speed**: 4-6x faster than sequential, fast enough for iterative development
- **Quality**: Complete coverage data for informed decisions
- **Stability**: Resource limits prevent system freezes and OOM errors
- **CI Parity**: Uses same split count as CI for consistency

**Key Takeaway**: Local parallel execution requires resource constraints that CI doesn't need. The script intelligently manages concurrency and workers to balance speed with system stability.

Use this script as your primary coverage testing tool during development. For detailed resource management and troubleshooting, see [PARALLEL_TESTING.md](PARALLEL_TESTING.md).

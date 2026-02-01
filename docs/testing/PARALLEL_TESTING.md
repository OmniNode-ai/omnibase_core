> **Navigation**: [Home](../index.md) > Testing > Parallel Testing Architecture

# Parallel Testing Architecture and Resource Management

This document explains the critical differences between CI parallel testing and local parallel testing, resource constraints, and best practices for avoiding resource exhaustion.

## Problem Statement

Running all 12 test splits in parallel on a local machine causes resource exhaustion, system freezes, and out-of-memory (OOM) errors. This happens because the local parallel coverage script tried to mimic CI's parallel execution model without accounting for fundamental architectural differences.

### The Root Cause

**CI Environment (Correct)**:
```
20 GitHub Actions runners (physically separate machines)
├─ Runner 1: Split 1 with -n auto (8-12 workers) ✅ Isolated resources
├─ Runner 2: Split 2 with -n auto (8-12 workers) ✅ Isolated resources
├─ Runner 3: Split 3 with -n auto (8-12 workers) ✅ Isolated resources
...
└─ Runner 20: Split 20 with -n auto (8-12 workers) ✅ Isolated resources

Total: 20 runners × ~10 workers = 200 workers across 20 SEPARATE machines ✅
```

**Local Environment (WRONG - Before Fix)**:
```
1 Local machine (single shared resource pool)
├─ Split 1 with -n auto (8-12 workers) ⚠️  Sharing CPU/memory
├─ Split 2 with -n auto (8-12 workers) ⚠️  Sharing CPU/memory
├─ Split 3 with -n auto (8-12 workers) ⚠️  Sharing CPU/memory
...
└─ Split 12 with -n auto (8-12 workers) ⚠️  Sharing CPU/memory

Total: 12 splits × ~10 workers = 120 workers on ONE machine ❌ Resource exhaustion
```

## Solution: Resource-Constrained Parallel Execution

The fixed script (`scripts/run-coverage-parallel.sh`) implements three critical constraints:

### 1. Concurrency Limit (Batch Execution)

**Problem**: Running all 12 splits simultaneously on one machine
**Solution**: Run only N splits at a time (default: 3)

```
# Configurable via environment variable
export MAX_CONCURRENT_SPLITS=3  # Only 3 splits run at once

# Script uses job control to enforce this limit
active_jobs=0
for i in {1..12}; do
  run_split $i &
  ((active_jobs++))

  if [[ $active_jobs -ge $MAX_CONCURRENT_SPLITS ]]; then
    wait -n  # Wait for ANY split to complete before launching next
    ((active_jobs--))
  fi
done
```

**Impact**:
- Before: 12 splits running simultaneously = resource exhaustion
- After: 3 splits running at a time = controlled resource usage
- Execution time: Slightly longer (5-10 minutes vs 3-5 minutes) but system remains responsive

### 2. Worker Limit (Explicit Worker Count)

**Problem**: Each split uses `-n auto` which spawns 8-12 workers
**Solution**: Explicitly set worker count to 2-4 per split

```
# Configurable via environment variable
export WORKERS_PER_SPLIT=4  # Only 4 workers per split

# Script passes explicit -n value instead of auto
poetry run pytest tests/ \
  --splits 12 \
  --group $split_num \
  -n $WORKERS_PER_SPLIT \  # Explicit control, not auto-detection
  ...
```

**Impact**:
- Before: 12 splits × 10 workers (auto) = 120 total workers ❌
- After: 3 concurrent splits × 4 workers = 12 total workers ✅

### 3. Fail-Fast with Max Failures

**Problem**: Tests continue running even after critical failures waste resources
**Solution**: Stop after N failures (default: 10)

```
# Configurable via environment variable
export MAX_FAILURES=10

# Script passes --maxfail to pytest
poetry run pytest tests/ \
  --maxfail=$MAX_FAILURES \  # Stop after 10 failures
  ...
```

**Impact**:
- Saves resources by stopping early on systematic failures
- Faster feedback when tests are fundamentally broken
- Reduces wasted CPU/memory on doomed test runs

## Resource Configuration Guide

### Recommended Configurations by Machine

| CPU Cores | RAM | MAX_CONCURRENT_SPLITS | WORKERS_PER_SPLIT | Total Workers | Execution Time |
|-----------|-----|----------------------|-------------------|---------------|----------------|
| 4-6 | 8-16 GB | 2 | 2-3 | 4-6 | 8-12 min |
| 8-10 | 16-32 GB | 3 | 4 | 12 | 5-8 min |
| 12-16 | 32-64 GB | 4 | 4-6 | 16-24 | 4-6 min |
| 16+ | 64+ GB | 4-6 | 6-8 | 24-48 | 3-5 min |

### How to Configure

**Option 1: Environment Variables (Temporary)**
```
# Set for single execution
export MAX_CONCURRENT_SPLITS=4
export WORKERS_PER_SPLIT=6
./scripts/run-coverage-parallel.sh
```

**Option 2: Inline Configuration (One-Time)**
```
# Override defaults inline
MAX_CONCURRENT_SPLITS=2 WORKERS_PER_SPLIT=3 ./scripts/run-coverage-parallel.sh
```

**Option 3: Shell Profile (Permanent)**
```
# Add to ~/.zshrc or ~/.bashrc
export MAX_CONCURRENT_SPLITS=3
export WORKERS_PER_SPLIT=4
export MAX_FAILURES=10
```

### Resource Warning System

The script automatically detects CPU count and warns if configuration is too aggressive:

```
🧪 Running parallel coverage tests (12 splits)
📊 Resource Configuration:
   • Concurrent splits: 3
   • Workers per split: 4
   • Total concurrent workers: 12
   • Max failures before abort: 10

⚠️  WARNING: Total workers (12) exceeds 2× CPU cores (8)
   This may cause resource exhaustion. Consider reducing:
   export MAX_CONCURRENT_SPLITS=2
   export WORKERS_PER_SPLIT=4
```

**Rule of Thumb**: Total workers should not exceed 2× CPU cores
- Formula: `MAX_CONCURRENT_SPLITS × WORKERS_PER_SPLIT ≤ 2 × CPU_COUNT`
- Example: 8 cores → max 16 workers → 3 splits × 4 workers = 12 ✅

## CI vs Local: Architectural Differences

### CI Execution Model (Horizontal Scaling)

```
# .github/workflows/test.yml
strategy:
  matrix:
    split: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

# GitHub Actions provisions 20 separate runners
# Each runner is a physically isolated VM with dedicated resources
# No resource contention between splits
```

**Characteristics**:
- **Isolation**: Each split runs on a separate VM (2 CPU cores, 7 GB RAM)
- **No Contention**: Splits don't compete for CPU/memory/I/O
- **Unlimited Workers**: `-n auto` is safe because resources are isolated
- **Cost Model**: Linear scaling (12 runners = 12× cost but 12× speed)

### Local Execution Model (Vertical Scaling with Constraints)

```
# scripts/run-coverage-parallel.sh
# Single machine runs multiple splits sequentially in controlled batches
# Shares CPU/memory/I/O across all active splits
# Requires explicit resource management
```

**Characteristics**:
- **Shared Resources**: All splits compete for CPU/memory/I/O on one machine
- **Contention Risk**: Without limits, processes compete and cause thrashing
- **Explicit Limits**: Must use concurrency + worker limits to prevent exhaustion
- **Cost Model**: No additional cost but requires careful resource tuning

### Key Takeaway

**Don't directly copy CI parallelization to local execution.**

CI's horizontal scaling (12 isolated runners) is fundamentally different from local vertical scaling (12 splits on one machine). Local execution requires resource constraints that CI doesn't need.

## Performance Characteristics

### Execution Time Analysis

| Configuration | Total Workers | Execution Time | System Load | Use Case |
|--------------|---------------|----------------|-------------|----------|
| **Sequential** | 1 | 30+ minutes | Low (10-20%) | Baseline reference |
| **CI (12 runners)** | 120 (isolated) | 3-5 minutes | Low per runner | Production CI |
| **Local (no limits)** | 120 (shared) | System freeze ❌ | 800%+ (thrashing) | Don't do this |
| **Local (3 splits × 4 workers)** | 12 | 5-8 minutes | Moderate (60-80%) | Recommended ✅ |
| **Local (4 splits × 6 workers)** | 24 | 4-6 minutes | High (90-100%) | High-end machines |

### Resource Usage Patterns

**CPU Usage**:
- Sequential: 10-20% average (single worker)
- Local parallel (constrained): 60-80% average (12 workers)
- Local parallel (unconstrained): 400-800% peak (thrashing, context switching overhead)

**Memory Usage**:
- Per pytest worker: ~200-500 MB
- 12 workers: ~2.4-6 GB total
- 120 workers: ~24-60 GB total (exceeds most machines)

**I/O Patterns**:
- Test collection: Reads thousands of test files (CPU-bound, benefits from parallelization)
- Test execution: Mostly CPU-bound with some disk I/O for fixtures
- Coverage writing: Each split writes separate `.coverage.N` file (no contention)

## Best Practices

### 1. Start Conservative, Then Tune

```
# Day 1: Start with conservative settings
export MAX_CONCURRENT_SPLITS=2
export WORKERS_PER_SPLIT=3
./scripts/run-coverage-parallel.sh

# Monitor system resources (Activity Monitor, htop)
# If system is responsive and CPU < 80%, increase gradually

# Day 2: Increase if system handled it well
export MAX_CONCURRENT_SPLITS=3
export WORKERS_PER_SPLIT=4
./scripts/run-coverage-parallel.sh
```

### 2. Monitor System Resources

**macOS**:
```
# Terminal 1: Run tests
./scripts/run-coverage-parallel.sh

# Terminal 2: Monitor resources
watch -n 1 'ps aux | grep pytest | wc -l'  # Worker count
top -o cpu  # CPU usage
```

**Linux**:
```
# Terminal 1: Run tests
./scripts/run-coverage-parallel.sh

# Terminal 2: Monitor resources
watch -n 1 'ps aux | grep pytest | wc -l'
htop  # Interactive process viewer
```

### 3. Adjust Based on Symptoms

**Symptom: System freeze or unresponsive UI**
- **Cause**: Too many concurrent workers
- **Solution**: Reduce `MAX_CONCURRENT_SPLITS` to 2

**Symptom: OOM (Out of Memory) errors**
- **Cause**: Too many workers consuming memory
- **Solution**: Reduce `WORKERS_PER_SPLIT` to 2-3

**Symptom: Slow execution (>10 minutes)**
- **Cause**: Too few workers, CPU underutilized
- **Solution**: Increase `MAX_CONCURRENT_SPLITS` or `WORKERS_PER_SPLIT`

**Symptom: High context switching overhead**
- **Cause**: Too many workers causing thrashing
- **Solution**: Reduce total workers to match CPU count (1:1 or 2:1 ratio)

### 4. Different Configurations for Different Tasks

```
# Quick sanity check (fast, minimal resources)
export MAX_CONCURRENT_SPLITS=2
export WORKERS_PER_SPLIT=2
export MAX_FAILURES=5
./scripts/run-coverage-parallel.sh

# Full coverage run (balanced, recommended)
export MAX_CONCURRENT_SPLITS=3
export WORKERS_PER_SPLIT=4
export MAX_FAILURES=10
./scripts/run-coverage-parallel.sh

# Pre-commit verification (aggressive, high-end machines only)
export MAX_CONCURRENT_SPLITS=4
export WORKERS_PER_SPLIT=6
export MAX_FAILURES=20
./scripts/run-coverage-parallel.sh
```

### 5. CI Parity Testing

To test a specific split exactly as CI runs it:

```
# CI runs each split in isolation with -n auto
# Replicate this locally:
COVERAGE_FILE=.coverage.1 poetry run pytest tests/ \
  --splits 20 \
  --group 1 \
  -n auto \
  --timeout=60 \
  --timeout-method=thread \
  --tb=short \
  -v
```

This tests a single split with CI's exact configuration (useful for debugging CI failures).

## Troubleshooting

### Issue: Script hangs during execution

**Symptoms**:
- Script stops producing output
- Processes stuck in "D" state (uninterruptible sleep)
- System load remains high but no progress

**Diagnosis**:
```
# Check for zombie/stuck processes
ps aux | grep pytest | grep -v grep

# Check process states
ps aux | grep "[D]"  # Uninterruptible sleep

# Check system load
uptime
```

**Solutions**:
1. **Kill stuck processes**:
   ```bash
   pkill -f "pytest tests/"
   killall pytest
   ```

2. **Reduce concurrency**:
   ```bash
   export MAX_CONCURRENT_SPLITS=2
   export WORKERS_PER_SPLIT=2
   ```

3. **Disable xdist entirely** (slowest but most reliable):
   ```bash
   # Edit script, change:
   # -n $WORKERS_PER_SPLIT
   # to:
   # (remove -n flag entirely for sequential execution per split)
   ```

### Issue: Memory exhaustion / OOM killer

**Symptoms**:
- `Killed` messages in terminal
- System swapping heavily
- Dmesg shows OOM killer activity: `dmesg | grep -i kill`

**Diagnosis**:
```
# Check available memory
free -h  # Linux
vm_stat  # macOS

# Check memory usage per worker
ps aux | grep pytest | awk '{sum+=$6} END {print sum/1024 " MB total"}'
```

**Solutions**:
1. **Reduce workers**:
   ```bash
   export MAX_CONCURRENT_SPLITS=2
   export WORKERS_PER_SPLIT=2
   ```

2. **Clear system cache** (Linux):
   ```bash
   sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
   ```

3. **Close other applications** to free memory

### Issue: Tests fail only in parallel, pass sequentially

**Symptoms**:
- Split N fails during parallel run
- Same tests pass when run individually
- Flaky failures with concurrency-related errors

**Diagnosis**:
```
# Run failing split sequentially
COVERAGE_FILE=.coverage.6 poetry run pytest tests/ \
  --splits 12 \
  --group 6 \
  -v  # No -n flag = sequential

# If it passes, it's a concurrency issue
```

**Solutions**:
1. **Check for shared state** in tests (global variables, singletons)
2. **Review test isolation** (conftest.py fixtures, cleanup)
3. **Add test markers** for isolation:
   ```python
   @pytest.mark.serial  # Run sequentially
   def test_shared_resource():
       ...
   ```

### Issue: Resource warning triggered

**Symptoms**:
```
⚠️  WARNING: Total workers (16) exceeds 2× CPU cores (8)
   This may cause resource exhaustion. Consider reducing:
   export MAX_CONCURRENT_SPLITS=2
   export WORKERS_PER_SPLIT=4
```

**Action**:
- This is a **warning, not an error**
- Script will still run, but watch for system responsiveness
- If system becomes sluggish, follow the warning's recommendations
- If system handles it fine, you can ignore (but monitor)

## Advanced Topics

### Optimal Worker Count Formula

**Theory**: Total workers should balance parallelism with overhead

```
Optimal Total Workers = (CPU Cores × Efficiency Factor) / Overhead Factor

Where:
- Efficiency Factor: 1.5-2.0 for CPU-bound tasks (test execution)
- Overhead Factor: 1.2-1.5 (context switching, coordination)

For 8-core machine:
Optimal = (8 × 1.5) / 1.2 = 10 workers

Split across 3 concurrent splits:
WORKERS_PER_SPLIT = 10 / 3 ≈ 3-4 workers
```

**In Practice**: Start with 2× CPU cores and adjust based on monitoring.

### Memory Profiling

To identify memory-heavy tests:

```
# Install memory profiler
poetry add --dev memory-profiler

# Profile specific test
poetry run python -m memory_profiler -m pytest tests/unit/specific_test.py -v

# Find memory-heavy fixtures
poetry run pytest tests/ --memprof --memprof-csv=memory.csv
```

### Custom Split Distribution

If certain splits consistently take longer, consider custom distribution:

```
# Option 1: Run slow splits first with more workers
WORKERS_PER_SPLIT=6 run_split 6 &  # Slow split
WORKERS_PER_SPLIT=4 run_split 1 &  # Normal split
WORKERS_PER_SPLIT=4 run_split 2 &  # Normal split

# Option 2: Increase total splits for better distribution
# Change from 12 to 16 splits for finer-grained parallelism
```

### Integration with CI

To replicate CI behavior exactly in local environment (for debugging):

```
# Create wrapper script that mimics CI matrix execution
for split in {1..12}; do
  echo "=== Running Split $split/12 (CI mode) ==="
  COVERAGE_FILE=.coverage.$split poetry run pytest tests/ \
    --splits 12 \
    --group $split \
    -n auto \
    --timeout=60 \
    --timeout-method=thread \
    --tb=short \
    --junitxml=junit-$split.xml
done
```

**Warning**: This will cause resource exhaustion (same as original problem). Only use for debugging specific splits, not full runs.

## Related Documentation

- [COVERAGE.md](COVERAGE.md) - Coverage testing overview and usage
- `.github/workflows/test.yml` - CI test configuration
- `scripts/run-coverage-parallel.sh` - Parallel coverage script

## Summary

**Key Principles**:
1. **CI ≠ Local**: CI's horizontal scaling requires different approach than local vertical scaling
2. **Resource Limits**: Always constrain concurrency and workers on local machines
3. **Monitor First**: Watch system resources before increasing parallelism
4. **Tune Gradually**: Start conservative, increase slowly based on evidence
5. **Fail Fast**: Use `--maxfail` to stop on systematic failures

**Default Configuration** (works for most machines):
```
export MAX_CONCURRENT_SPLITS=3
export WORKERS_PER_SPLIT=4
export MAX_FAILURES=10
./scripts/run-coverage-parallel.sh
```

**Expected Results**:
- Execution time: 5-8 minutes (vs 30+ sequential, vs 3-5 CI)
- System load: 60-80% CPU (responsive, not frozen)
- Total workers: 12 (safe for 8+ core machines)
- Coverage accuracy: Identical to sequential runs

The resource-constrained approach provides the best balance between speed, system stability, and coverage accuracy for local development.

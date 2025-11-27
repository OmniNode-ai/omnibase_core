# CI Monitoring Guide - omnibase_core

> **Purpose**: Operational guidance for detecting, investigating, and resolving CI performance anomalies
> **Last Updated**: 2025-11-01
> **Baseline Source**: [CI Run #18997947041](https://github.com/OmniNode-ai/omnibase_core/actions/runs/18997947041)

---

## Table of Contents

1. [Overview](#overview)
2. [Baseline Metrics](#baseline-metrics)
3. [Monitoring Strategy](#monitoring-strategy)
4. [Alert Thresholds](#alert-thresholds)
5. [Investigation Workflow](#investigation-workflow)
6. [Common Issues & Resolutions](#common-issues--resolutions)
7. [Metrics to Track](#metrics-to-track)
8. [Tools & Commands](#tools--commands)
9. [Historical Analysis](#historical-analysis)

---

## Overview

The omnibase_core test suite runs across **20 parallel splits** in GitHub Actions. This guide provides operational procedures for monitoring CI health, detecting performance regressions, and investigating anomalies.

### Key Principles

- **Proactive Monitoring**: Track trends before failures occur
- **Data-Driven Alerts**: Use baseline benchmarks to define thresholds
- **Fast Investigation**: Structured debugging workflow
- **Continuous Improvement**: Learn from anomalies to prevent recurrence

### When to Use This Guide

- ✅ **Daily/Weekly**: Review CI performance trends
- ✅ **On Alert**: Investigate splits exceeding thresholds
- ✅ **Post-Incident**: Root cause analysis after failures
- ✅ **Quarterly**: Baseline updates and capacity planning

---

## Baseline Metrics

**Configuration**: 20 parallel splits, GitHub Actions runners, ~12,198 tests total

### Current Baseline (2025-11-01)

| Metric | Value | Source |
|--------|-------|--------|
| **Average Runtime** | 2m58s per split | CI Run #18997947041 |
| **Fastest Split** | 2m35s (Split 6/20) | CI Run #18997947041 |
| **Slowest Split** | 3m35s (Split 12/20) | CI Run #18997947041 |
| **Runtime Range** | 60s variation | CI Run #18997947041 |
| **Total CI Time** | ~3-4 minutes (parallel) | CI Run #18997947041 |
| **Tests per Split** | ~610 tests (12,198 ÷ 20) | Test collection |

### Split-by-Split Baseline

```
Split  1/20: 2m49s    Split 11/20: 2m52s
Split  2/20: 3m1s     Split 12/20: 3m35s ⚠️  (slowest)
Split  3/20: 2m44s    Split 13/20: 2m56s
Split  4/20: 3m8s     Split 14/20: 2m57s
Split  5/20: 2m47s    Split 15/20: 2m53s
Split  6/20: 2m35s ✅  (fastest)   Split 16/20: 3m12s
Split  7/20: 2m55s    Split 17/20: 3m1s
Split  8/20: 2m58s    Split 18/20: 2m56s
Split  9/20: 3m5s     Split 19/20: 3m1s
Split 10/20: 2m56s    Split 20/20: 2m58s
```

**Interpretation**:
- **Normal Range**: 2m35s - 3m35s (60s spread)
- **Average**: 2m58s ± 15s
- **Outliers**: Split 12 consistently slower (heavier test distribution)

---

## Monitoring Strategy

### 1. Daily Monitoring

**Frequency**: Every CI run (automated via GitHub Actions)

**Metrics to Track**:
- Individual split durations
- Total CI runtime
- Test failure rate
- Resource warnings (memory, timeout)

**Tools**:
- GitHub Actions UI (workflow run summary)
- `gh run view <run-id>` (CLI)
- CI email notifications (on failure)

**Action**: Review dashboard, note any anomalies

### 2. Weekly Analysis

**Frequency**: Every Monday (or after 20+ CI runs)

**Metrics to Track**:
- Average split duration trend (7-day rolling)
- Slowest split identification
- Failure rate by split
- Test count distribution

**Tools**:
- GitHub Actions API
- Custom reporting scripts (see [Tools & Commands](#tools--commands))
- Manual spreadsheet tracking

**Action**: Update baselines if significant changes detected

### 3. Monthly Review

**Frequency**: First of each month

**Metrics to Track**:
- 30-day performance trends
- Capacity planning (test count growth)
- Split rebalancing needs
- Runner resource utilization

**Tools**:
- GitHub insights
- Historical CSV export
- Quarterly benchmark comparison

**Action**: Plan optimizations, update documentation

---

## Alert Thresholds

### Severity Levels

Based on baseline metrics (2m58s average, 2m35s-3m35s range):

| Severity | Duration | Action | Response Time |
|----------|----------|--------|---------------|
| **🟢 Normal** | 2m30s - 3m30s | None - within expected range | N/A |
| **🟡 Warning** | 3m30s - 4m30s | Review split, monitor next run | Within 1 business day |
| **🟠 Critical** | 4m30s - 6m00s | Investigate immediately | Within 4 hours |
| **🔴 Emergency** | > 6m00s | Incident response, rollback if needed | Immediate |

### Threshold Rationale

- **Normal (2m30s - 3m30s)**: Baseline range ± 30s buffer
- **Warning (3m30s - 4m30s)**: 1.5x baseline variation (investigate but not urgent)
- **Critical (4m30s - 6m00s)**: 2x baseline variation (likely regression)
- **Emergency (> 6m00s)**: 2x+ baseline variation (blocking issue)

### Alert Triggers

Trigger alerts when:
1. **Single split** exceeds warning threshold (3m30s)
2. **3+ splits** exceed normal range in same run
3. **Average runtime** increases >20% over 7-day baseline
4. **Any split** times out (>10 minutes)
5. **Total CI time** exceeds 6 minutes

### Alert Channels

- **GitHub Actions**: Built-in failure notifications
- **Email**: Workflow failure summaries
- **Slack** (if configured): CI status bot
- **Manual**: Review runs daily in GitHub UI

---

## Investigation Workflow

### Step 1: Identify the Anomaly

**Command**:
```
# View recent CI run summary
gh run view <run-id>

# List all runs for comparison
gh run list --workflow=test.yml --limit 10
```

**Questions to Answer**:
- Which split(s) are slow?
- Is this a one-time spike or trend?
- Are other splits also affected?
- What changed since the last run?

**Output Example**:
```
✓ test / test (20 splits) / split-12 (2025-11-01T10:35:42Z)
  Duration: 4m25s ⚠️ WARNING (exceeds 3m30s threshold)
```

### Step 2: Check Test Distribution

**Command**:
```
# Collect tests in specific split (local simulation)
poetry run pytest --collect-only --splits=20 --group=12

# Count tests per split
poetry run pytest --collect-only --quiet | wc -l
```

**Questions to Answer**:
- How many tests are in the slow split?
- Are there known slow tests in this group?
- Is the distribution balanced?

**Expected Output**:
```
Split 12/20: 653 tests collected
Average per split: 610 tests
Variance: +43 tests (+7%)
```

**Action**:
- If variance >15%: Consider rebalancing splits
- If test count normal: Proceed to profiling

### Step 3: Profile Slow Tests

**Command**:
```
# Run slow split with duration reporting
poetry run pytest tests/ \
  --splits=20 --group=12 \
  --durations=20 \
  --timeout=60 \
  -v

# Alternative: Run with detailed timing
poetry run pytest tests/ \
  --splits=20 --group=12 \
  --durations=0 | sort -t: -k2 -n | tail -20
```

**Questions to Answer**:
- Which tests are slowest?
- Are there outliers (>10s per test)?
- Are there fixtures causing delays?
- Are tests hanging/timing out?

**Expected Output**:
```
slowest durations:
15.23s call     tests/unit/models/test_large_model.py::test_complex_validation
12.45s call     tests/unit/nodes/test_orchestrator_workflow.py::test_multi_step
8.92s setup    tests/integration/test_database_fixture.py::test_transaction
```

**Action**:
- If outliers >10s: Mark with `@pytest.mark.slow`
- If fixture delays: Optimize setup/teardown
- If timeouts: Investigate event loop issues

### Step 4: Review Resource Usage

**Location**: GitHub Actions run logs → Job details → Resource usage

**Metrics to Check**:
- Peak memory usage
- CPU utilization
- Disk I/O
- Network calls (if applicable)

**Questions to Answer**:
- Is the runner out of resources?
- Are tests competing for resources?
- Is `-n auto` spawning too many workers?

**Typical Issues**:
- Memory exhaustion with parallel workers
- CPU throttling on shared runners
- Fixture teardown delays

**Action**:
- If memory high: Reduce `-n auto` workers for this split
- If CPU throttled: Consider dedicated runner
- If I/O bound: Mock external dependencies

### Step 5: Compare with Historical Data

**Command**:
```
# List recent runs with durations
gh run list --workflow=test.yml --json databaseId,conclusion,createdAt,updatedAt --limit 20

# View specific run
gh run view <run-id> --log | grep "split-12"
```

**Questions to Answer**:
- Is this a new regression?
- When did the slowdown start?
- What commits are between runs?

**Action**:
- If new regression: Bisect commits to find cause
- If ongoing issue: Plan optimization work
- If external factor: Document and monitor

### Step 6: Root Cause Analysis

**Common Root Causes**:

| Symptom | Likely Cause | Investigation | Resolution |
|---------|--------------|---------------|------------|
| Single split slow | Unbalanced test distribution | Check test count | Rebalance splits |
| All splits slow | Environment issue | Check runner status | Retry workflow |
| Gradual slowdown | Test suite growth | Track test count | Increase split count |
| Intermittent spikes | Resource contention | Check parallel workers | Reduce `-n auto` |
| New test causing delay | Slow test logic | Profile test duration | Optimize or mark slow |
| Fixture delays | Heavy setup/teardown | Profile fixture time | Mock dependencies |

**Action**: Document findings in incident report

### Step 7: Implement Resolution

**Short-Term Fixes**:
- Retry workflow (if transient)
- Disable problematic test (if blocking)
- Increase timeout for specific test
- Reduce parallel workers for split

**Long-Term Solutions**:
- Rebalance split distribution
- Optimize slow tests
- Increase split count (e.g., 20 → 24)
- Upgrade runner resources
- Refactor fixtures

**Verification**:
```
# Run affected split locally to verify fix
poetry run pytest tests/ --splits=20 --group=12 --durations=10

# Push fix and monitor next CI run
git push && gh run watch
```

---

## Common Issues & Resolutions

### Issue 1: Split 12 Consistently Slower

**Symptoms**:
- Split 12/20 runs 3m35s (60s slower than average)
- Other splits run 2m30s - 3m10s
- Test count balanced (~610 tests/split)

**Root Cause**: Split 12 contains heavier integration tests

**Investigation**:
```
# Identify slow tests in split 12
poetry run pytest --collect-only --splits=20 --group=12 | grep integration
poetry run pytest tests/ --splits=20 --group=12 --durations=20
```

**Resolution**:
- ✅ **Accepted variance** (within 60s baseline range)
- Monitor for future increases
- Consider marking slowest tests with `@pytest.mark.slow`
- If exceeds 4m: Rebalance or increase splits

### Issue 2: All Splits Suddenly Slow

**Symptoms**:
- Average runtime increases from 2m58s → 4m30s
- All 20 splits affected equally
- No code changes

**Root Cause**: GitHub Actions runner performance degradation

**Investigation**:
```
# Check GitHub Actions status
curl https://www.githubstatus.com/api/v2/status.json

# Compare multiple recent runs
gh run list --workflow=test.yml --limit 5
```

**Resolution**:
- Retry workflow
- If persistent: File GitHub support ticket
- Temporary: Increase timeout thresholds
- Long-term: Consider self-hosted runners

### Issue 3: Test Count Growth Slowing CI

**Symptoms**:
- Test suite grows from 10,000 → 12,198 → 15,000+
- Average split duration increases proportionally
- No individual slow tests

**Root Cause**: Natural test suite growth

**Investigation**:
```
# Track test count over time
git log --all --pretty=format:"%h %ad" --date=short | while read commit date; do
  git checkout $commit 2>/dev/null
  count=$(poetry run pytest --collect-only --quiet 2>/dev/null | grep "test" | wc -l)
  echo "$date,$commit,$count"
done > test_growth.csv
```

**Resolution**:
- Increase split count (20 → 24 → 30)
- Evaluate split count formula: `splits = ceil(test_count / 500)`
- Maintain target: 2-4 minutes per split
- Update CLAUDE.md benchmarks

### Issue 4: Event Loop Hangs in CI

**Symptoms**:
- Tests timeout after 60s
- Hangs during async fixture teardown
- Works locally, fails in CI

**Root Cause**: Unclosed event loops or background tasks

**Investigation**:
```
# Run with detailed async debugging
poetry run pytest tests/ \
  --splits=20 --group=12 \
  --log-cli-level=DEBUG \
  --capture=no \
  -xvs

# Check for event loop warnings
grep "Event loop" <ci-log-file>
```

**Resolution**:
- Ensure `pytest-asyncio` mode: `asyncio_mode = auto`
- Add explicit cleanup in fixtures
- Use `@pytest.mark.asyncio` decorators
- Review event loop cleanup in async fixtures

### Issue 5: Memory Exhaustion

**Symptoms**:
- Runner killed by OOM (out of memory)
- Tests fail with "MemoryError"
- Occurs with `-n auto` parallelism

**Root Cause**: Too many parallel workers or memory-intensive tests

**Investigation**:
```
# Run with reduced workers
poetry run pytest tests/ --splits=20 --group=12 -n 2

# Profile memory usage (local)
poetry run pytest tests/ --memray --splits=20 --group=12
```

**Resolution**:
- Reduce parallel workers: `-n auto` → `-n 2` or `-n 0`
- Split memory-intensive tests into separate group
- Increase runner memory (paid plan)
- Optimize test fixtures to reduce memory footprint

---

## Metrics to Track

### Primary Metrics (Required)

| Metric | Target | Threshold | Collection Method |
|--------|--------|-----------|-------------------|
| **Split Duration** | 2m30s - 3m30s | >3m30s warning | GitHub Actions UI |
| **Average Runtime** | 2m58s ± 15s | >3m30s warning | Calculated from all splits |
| **Total CI Time** | 3-4 minutes | >6m warning | GitHub Actions workflow time |
| **Test Count** | ~12,198 tests | Track growth | `pytest --collect-only` |
| **Failure Rate** | <1% | >5% critical | CI run history |

### Secondary Metrics (Recommended)

| Metric | Target | Purpose | Collection Method |
|--------|--------|---------|-------------------|
| **Slowest Split** | <3m35s | Identify imbalances | Max duration across splits |
| **Runtime Variance** | <60s | Detect distribution issues | Max - Min split duration |
| **Tests per Split** | ~610 ± 50 | Balance splits | `pytest --collect-only` per split |
| **Timeout Rate** | 0 timeouts | Detect hangs | CI logs |
| **Memory Peak** | <6GB | Resource planning | GitHub runner metrics |

### Tertiary Metrics (Optional)

| Metric | Purpose | Collection Method |
|--------|---------|-------------------|
| **Coverage Trend** | Track code quality | Coverage reports (main only) |
| **Flaky Test Rate** | Identify unstable tests | Retry analysis |
| **CI Cost** | Budget tracking | GitHub billing API |
| **Test Duration Outliers** | Optimization targets | `--durations=20` |

---

## Tools & Commands

### GitHub CLI (`gh`)

```
# Install GitHub CLI (if not already installed)
brew install gh  # macOS
# or: https://cli.github.com/

# Authenticate
gh auth login

# View latest CI run
gh run list --workflow=test.yml --limit 1

# View specific run details
gh run view <run-id>

# Download run logs for analysis
gh run download <run-id>

# Watch current run in real-time
gh run watch

# Rerun failed jobs
gh run rerun <run-id>
```

### Local Testing Commands

```
# Simulate specific split locally
poetry run pytest tests/ --splits=20 --group=12

# Profile slowest tests in split
poetry run pytest tests/ \
  --splits=20 --group=12 \
  --durations=20 \
  --timeout=60

# Collect tests in split (no execution)
poetry run pytest --collect-only \
  --splits=20 --group=12

# Run with detailed timing
poetry run pytest tests/ \
  --splits=20 --group=12 \
  -v --tb=short \
  --durations=0 | tee split_12_timing.log
```

### Custom Monitoring Scripts

**Example script (create locally if needed)**:

The following is an example monitoring script you can create locally. It is not included in the repository as it depends on local `gh` CLI configuration.

```bash
#!/bin/bash
# Example: scripts/monitor_ci.sh (create locally if needed)
# Monitor CI performance across recent runs

RUNS=10
echo "Analyzing last $RUNS CI runs..."

gh run list --workflow=test.yml --limit $RUNS --json databaseId,createdAt,conclusion | \
  jq -r '.[] | "\(.databaseId) \(.createdAt) \(.conclusion)"' | \
  while read run_id created_at conclusion; do
    echo "Run: $run_id ($conclusion) - $created_at"
    # Extract split durations (requires parsing logs)
  done
```

**Create `scripts/analyze_split_times.py`**:
```
#!/usr/bin/env python3
"""Analyze split durations from CI logs."""
import json
import sys
from statistics import mean, stdev

# Parse CI log and extract split durations
# (Implementation depends on log format)

def analyze_splits(log_file):
    durations = []
    # Parse log file
    # Extract "split-X/20 ... Duration: Xm Ys"
    return {
        "average": mean(durations),
        "stdev": stdev(durations),
        "min": min(durations),
        "max": max(durations),
    }

if __name__ == "__main__":
    results = analyze_splits(sys.argv[1])
    print(json.dumps(results, indent=2))
```

### Reporting Dashboard (Manual)

**Spreadsheet Template**: Track weekly CI performance

| Date | Run ID | Avg Split | Slowest Split | Total CI Time | Test Count | Notes |
|------|--------|-----------|---------------|---------------|------------|-------|
| 2025-11-01 | 18997947041 | 2m58s | 3m35s (Split 12) | 4m12s | 12,198 | Baseline |
| 2025-11-08 | ... | ... | ... | ... | ... | ... |

**Google Sheets Formula** (for trend analysis):
```
=AVERAGE(C2:C10)  // Average of last 10 runs
=SPARKLINE(C2:C10)  // Visual trend
=IF(C2>210,"⚠️ WARNING","✅ OK")  // Alert if >3m30s
```

---

## Historical Analysis

### Tracking Long-Term Trends

**Weekly Review Process**:

1. **Export Data**:
   ```bash
   # Export last 30 runs to CSV
   gh run list --workflow=test.yml --limit 30 --json databaseId,createdAt,updatedAt,conclusion > ci_history.json
   ```

2. **Calculate Metrics**:
   ```python
   import json
   from datetime import datetime

   with open('ci_history.json') as f:
       runs = json.load(f)

   for run in runs:
       created = datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00'))
       updated = datetime.fromisoformat(run['updatedAt'].replace('Z', '+00:00'))
       duration = (updated - created).total_seconds() / 60
       print(f"{run['databaseId']},{created.date()},{duration:.1f}m,{run['conclusion']}")
   ```

3. **Visualize Trends** (Google Sheets, Excel, or Python):
   - Plot average split duration over time
   - Identify upward trends
   - Correlate with test count growth
   - Mark optimization milestones

### Baseline Update Schedule

**When to Update Baselines**:

1. **After Major Optimizations**:
   - Split count change (e.g., 20 → 24)
   - Test parallelism adjustments
   - Runner upgrades

2. **Quarterly Reviews**:
   - Jan 1, Apr 1, Jul 1, Oct 1
   - Compare current vs. baseline
   - Update CLAUDE.md if significant drift (>20%)

3. **After Test Suite Growth**:
   - Every 2,000 test increase
   - Recalculate tests per split
   - Adjust thresholds proportionally

**Baseline Update Process**:

1. Select representative CI run (successful, recent, no anomalies)
2. Document run ID and date
3. Update CLAUDE.md CI Performance Benchmarks section
4. Update this guide's baseline metrics
5. Commit with message: `docs: update CI baseline metrics (run #XXXXX)`

### Historical Context

| Date | Test Count | Split Count | Avg Runtime | Notable Changes |
|------|------------|-------------|-------------|-----------------|
| 2024-11-01 | ~10,000 | 10 splits | ~4m30s | Initial configuration |
| 2024-12-15 | ~10,987 | 12 splits | ~3m45s | First optimization |
| 2025-01-15 | ~11,500 | 16 splits | ~3m10s | Event loop fixes |
| 2025-11-01 | 12,198 | 20 splits | 2m58s | **Current baseline** |

**Growth Trend**: +2,198 tests over 6 months (~366 tests/month)

**Next Review**: When test count reaches 15,000 or avg runtime exceeds 3m30s

---

## Summary: Quick Reference

### Alert Response Matrix

| Observation | Severity | Response | Timeline |
|-------------|----------|----------|----------|
| Split 2m30s - 3m30s | 🟢 Normal | None | - |
| Split 3m30s - 4m30s | 🟡 Warning | Review next run | 1 business day |
| Split 4m30s - 6m00s | 🟠 Critical | Investigate immediately | 4 hours |
| Split > 6m00s | 🔴 Emergency | Incident response | Immediate |
| All splits slow | 🟠 Critical | Check runner status | 4 hours |
| Timeout (>10m) | 🔴 Emergency | Bisect and rollback | Immediate |

### Investigation Checklist

- [ ] Identify slow split(s) via `gh run view <run-id>`
- [ ] Check test distribution: `pytest --collect-only --splits=20 --group=X`
- [ ] Profile slow tests: `pytest --durations=20 --splits=20 --group=X`
- [ ] Review resource usage in GitHub Actions logs
- [ ] Compare with historical data: `gh run list --workflow=test.yml --limit 10`
- [ ] Document root cause and resolution
- [ ] Update baselines if needed

### Quick Commands

```
# View latest CI run
gh run view $(gh run list --workflow=test.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# Run slow split locally with profiling
poetry run pytest tests/ --splits=20 --group=12 --durations=20

# Monitor CI in real-time
gh run watch
```

---

## References

- **[CLAUDE.md](../../CLAUDE.md#ci-performance-benchmarks)** - CI Performance Benchmarks section
- **[CI_TEST_STRATEGY.md](../testing/CI_TEST_STRATEGY.md)** - Overall CI test strategy
- **[PARALLEL_TESTING.md](../testing/PARALLEL_TESTING.md)** - Parallel testing configuration
- **GitHub Actions Workflow**: [`.github/workflows/test.yml`](../../.github/workflows/test.yml)
- **GitHub CLI Docs**: https://cli.github.com/manual/

---

**Last Updated**: 2025-11-01
**Baseline Version**: v1.0 (Run #18997947041)
**Next Review**: 2025-12-01 or when avg runtime exceeds 3m30s
**Correlation ID**: `95cac850-05a3-43e2-9e57-ccbbef683f43`

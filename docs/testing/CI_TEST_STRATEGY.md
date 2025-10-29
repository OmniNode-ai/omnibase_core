# CI Test Strategy - omnibase_core

## Overview

This document outlines the comprehensive CI/CD test strategy for omnibase_core, balancing speed, coverage, and cost-effectiveness across different workflow stages.

## Current Test Suite Stats

- **Total Tests**: 10,987 tests (updated from 11,446 - split optimization)
- **Test Categories**: Unit (400+), Integration, Validation, Nodes, Models, Mixins
- **Parallel Splits**: 16 splits (~687 tests/split)
- **Execution Time**:
  - Smoke tests: 5-10 seconds
  - Full suite (parallel): 2-4 minutes per split, ~4 minutes total (16x parallelism)
  - Full suite (sequential): ~60-80 minutes
- **Coverage Requirement**: 60% minimum (fail_under=60)

## Test Execution Matrix

| Trigger | Smoke | Full Suite | Coverage | Lint | Docs | Total Time |
|---------|-------|------------|----------|------|------|------------|
| **PR → develop** | ✅ Yes | ✅ Yes (16 splits) | ❌ No | ✅ Yes | ✅ Yes | ~5-7 min |
| **PR → main** | ✅ Yes | ✅ Yes (16 splits) | ✅ Yes | ✅ Yes | ✅ Yes | ~20 min |
| **Push → develop** | ✅ Yes | ✅ Yes (16 splits) | ❌ No | ✅ Yes | ✅ Yes | ~5-7 min |
| **Push → main** | ✅ Yes | ✅ Yes (16 splits) | ✅ Yes | ✅ Yes | ✅ Yes | ~20 min |
| **Release build** | ✅ Yes | ✅ Yes (16 splits) | ✅ Yes | ✅ Yes | ✅ Yes | ~20 min |

## CI Job Breakdown

### 1. Smoke Tests (5-10s)
**Purpose**: Fail-fast on basic issues
**Scope**: Core enums, errors, basic functionality
**Trigger**: All pushes and PRs
**Configuration**:
```yaml
poetry run pytest tests/unit/enums tests/unit/errors \
  --maxfail=5 -x --tb=short
```

**Why smoke tests?**
- 🚀 10-second feedback on fundamental breakage
- 💰 Prevents wasted CI resources on obviously broken builds
- ✅ Validates environment setup before expensive parallel runs

### 2. Parallel Test Execution (16 splits, ~4 min total)
**Purpose**: Comprehensive test validation with optimal speed/resource balance
**Scope**: All 10,987 tests split into 16 groups
**Trigger**: All pushes and PRs
**Configuration**:
```yaml
poetry run pytest tests/ \
  --splits 16 --group ${{ matrix.split }} \
  -n auto --timeout=60 --tb=short
```

**Split Strategy Rationale**:
- 10,987 tests ÷ 16 = ~687 tests/split
- Target: 2-4 minutes per split (reduces runner cancellation)
- 16x parallelization vs sequential execution
- Increased from 12 to 16 to reduce Split 7 cancellations
- `-n auto` for additional parallelism within each split

**Why 16 splits?**
- ⚡ Faster feedback (4 min vs 60+ min sequential)
- 🔄 Reduced runner cancellation exposure
- 💾 Better memory management (~687 tests/runner)
- 🎯 Optimal cost/speed trade-off

### 3. Coverage Report (15 min)
**Purpose**: Track code coverage and enforce minimum thresholds
**Scope**: Full test suite with coverage instrumentation
**Trigger**: **UPDATED** - Push to main OR PR to main
**Configuration**:
```yaml
if: github.ref == 'refs/heads/main' ||
    (github.event_name == 'pull_request' && github.base_ref == 'main')

poetry run pytest tests/ \
  -n auto \
  --cov=src/omnibase_core \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-report=html \
  --cov-fail-under=60
```

**Coverage Strategy**:
- ✅ **Main branch**: Track overall coverage trends
- ✅ **PRs to main**: Validate production-bound changes
- ❌ **PRs to develop**: Skipped (saves ~15 min CI time)
- 📊 **Reports**: Terminal, XML (CI tools), HTML (artifacts)

**Why skip coverage on develop PRs?**
- 💰 Saves ~15 minutes per PR (~30 CI credits)
- 🚀 Faster feedback for feature development
- ✅ Coverage validated before main merge anyway
- 🔧 Developers can run coverage locally with testmon

### 4. Code Quality (Lint) (5-10 min)
**Purpose**: Enforce code quality standards
**Scope**: Black, isort, mypy strict mode
**Trigger**: All pushes and PRs
**Configuration**:
```yaml
poetry run black --check src/ tests/
poetry run isort --check-only src/ tests/
poetry run mypy src/omnibase_core  # Strict mode: 0 errors across 1865 files
```

**Why always lint?**
- ✅ Enforces consistent code style
- 🔒 100% mypy strict compliance (0 errors)
- 🚫 Prevents technical debt accumulation
- 📝 Fast feedback on formatting issues

### 5. Documentation Validation (1-2 min)
**Purpose**: Ensure documentation integrity
**Scope**: Link validation, case sensitivity
**Trigger**: All pushes and PRs
**Configuration**:
```yaml
python3 scripts/validate-doc-links.py --fix-case
```

**Why validate docs in CI?**
- 📚 Catches broken documentation links early
- ✅ Ensures docs stay in sync with code
- 🔗 Validates cross-references and navigation

## Recommended Local Development Workflow

### Fast Iteration (Recommended)
```bash
# 1. Run only affected tests (10x-100x faster)
poetry run pytest --testmon

# 2. Add coverage if needed
poetry run pytest --testmon --cov --cov-report=term-missing

# 3. Reset testmon after major refactor
poetry run pytest --testmon-noselect
```

**Speedup Example**: 10,987 tests → ~50 tests for small changes (~220x faster)

### Pre-Commit Validation
```bash
# Run affected tests with coverage
poetry run pytest --testmon --cov --cov-fail-under=60

# Format and lint
poetry run black src/ tests/
poetry run isort src/ tests/
poetry run mypy src/omnibase_core
```

### Full Suite (Before Push to Main)
```bash
# Run complete test suite
poetry run pytest tests/

# With coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing
```

## Test Selection Strategy

### When to Run What Tests?

| Scenario | Recommended Approach | Time | Coverage |
|----------|---------------------|------|----------|
| **Local file edit** | `pytest --testmon` | <30s | Affected code |
| **Feature development** | `pytest --testmon --cov` | <1 min | Affected code |
| **Before commit** | `pytest --testmon` + lint | <2 min | Affected code |
| **Before PR** | `pytest tests/` (full) | ~5 min | Full suite |
| **Before main merge** | Full CI suite | ~20 min | Full coverage |
| **Release prep** | Full CI + manual tests | ~30 min | Full coverage |

## CI Cost Optimization

### Current Costs (GitHub Actions minutes)

| Workflow | Minutes | Frequency | Monthly Cost |
|----------|---------|-----------|--------------|
| PR to develop | ~7 min | 20/month | ~140 min |
| PR to main | ~20 min | 5/month | ~100 min |
| Push to main | ~20 min | 20/month | ~400 min |
| **Total** | - | - | **~640 min/month** |

**Cost Reduction Strategy**:
1. ✅ Skip coverage on develop PRs (saves ~300 min/month)
2. ✅ Use pytest-testmon locally (reduces unnecessary CI runs)
3. ✅ Optimize split count (16 splits = optimal speed/cost)
4. ✅ Smoke tests prevent wasted parallel runs

## CI Failure Scenarios & Response

### Smoke Test Failure
**Response**: Fix immediately (fundamental breakage)
**Impact**: Blocks all downstream jobs
**Typical Causes**: Import errors, syntax errors, missing dependencies

### Parallel Test Failure
**Response**: Review failing split, run locally to debug
**Impact**: Blocks PR merge, coverage report
**Typical Causes**: Test logic errors, race conditions, environment issues

### Coverage Failure (fail_under=60)
**Response**: Add tests or justify exemption
**Impact**: Blocks main merge (not develop PRs)
**Typical Causes**: New code without tests, removed test files

### Lint Failure
**Response**: Run formatters locally and push
**Impact**: Blocks PR merge
**Typical Causes**: Formatting issues, type errors, import order

## Future Optimizations

### Phase 1: Implemented ✅
- ✅ pytest-testmon for local development
- ✅ Coverage conditional on branch (main only)
- ✅ 16 parallel splits for optimal speed
- ✅ Smoke tests for fail-fast validation

### Phase 2: Planned (Q2 2025)
- ⏳ Differential testing on PRs (testmon in CI)
- ⏳ Test result caching between runs
- ⏳ Flaky test detection and retry
- ⏳ Performance regression testing

### Phase 3: Future (Q3 2025)
- 🔮 ML-based test selection
- 🔮 Predictive test prioritization
- 🔮 Intelligent coverage sampling
- 🔮 Distributed test execution (self-hosted)

## Summary: Answer to "Full Suite or Release Only?"

### ✅ Recommended Strategy (Current)

**PRs & Feature Branches**: Full suite (16 splits)
- **Rationale**: 10,987 tests run in ~4 min with parallelism (acceptable speed)
- **Benefit**: Catch issues early, prevent broken merges
- **Cost**: ~7 min per develop PR, ~20 min per main PR

**Coverage**: Main branch + PRs to main only
- **Rationale**: Expensive (~15 min), less critical for develop
- **Benefit**: Production-critical validation, trend tracking
- **Cost**: ~15 min per main-bound workflow

**Local Development**: pytest-testmon (smart selection)
- **Rationale**: 10x-100x faster iteration for developers
- **Benefit**: Fast feedback without CI overhead
- **Cost**: Minimal (local compute only)

### ❌ Not Recommended Alternatives

**Release-Only Full Suite**:
- ❌ Catches issues too late (wasted development time)
- ❌ Broken code accumulates in develop branch
- ❌ Higher risk of integration failures

**Full Suite Always (No Splits)**:
- ❌ 60+ minutes per run (unacceptable feedback loop)
- ❌ Expensive CI costs (10x current)
- ❌ Blocks developer productivity

## References

- [pytest-testmon Documentation](https://github.com/tarpas/pytest-testmon)
- [TESTMON_USAGE.md](./TESTMON_USAGE.md) - Local testmon usage guide
- [pytest.ini Configuration](../../pyproject.toml) - Test configuration
- [CI Workflow](../../.github/workflows/test.yml) - GitHub Actions configuration

---

**Last Updated**: 2025-10-29
**Test Suite Version**: 0.1.1 (10,987 tests)
**CI Strategy Version**: v2.0 (16 splits + conditional coverage)

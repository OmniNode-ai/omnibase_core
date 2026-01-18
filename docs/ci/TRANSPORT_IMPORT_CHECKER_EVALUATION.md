> **Navigation**: [Home](../index.md) > CI > Transport Import Checker Evaluation

# Transport Import Checker: `--changed-files` Mode Evaluation

**Linear Ticket**: [OMN-651](https://linear.app/omninode/issue/OMN-651)
**Related PR**: #147 (original implementation)
**Date**: 2025-12-10
**Status**: Evaluation Complete - Recommended for Implementation
**Version**: 1.1 (incorporates review feedback)

---

## Executive Summary

This document evaluates the feasibility and benefits of using `--changed-files` mode for the transport import checker (`scripts/check_transport_imports.py`) in CI.

**Recommendation**: **Implement Option B+ (Enhanced Hybrid Approach)**
- Use `--changed-files` for fast PR feedback on non-protected branch PRs
- Run full scan only for PRs targeting protected branches (main/develop)
- Run full scan only on pushes to protected branches (main/develop)

**Expected Impact**:
- **82% faster** CI feedback for typical PRs targeting non-protected branches
- **No additional risk** on protected branches compared to current full scan
- **Improved developer experience** with faster iteration cycles

**Honest Assessment**: At current scale (~2k files, 2.6s full scan), the absolute time savings are modest. The primary justification is forward-looking: as the codebase grows toward 5k+ files, the optimization becomes increasingly valuable.

---

## 1. Performance Benchmarks

### Test Environment
- **Codebase**: omnibase_core v0.4.0
- **Total Python Files**: 1,998 files in `src/omnibase_core/`
- **Hardware**: CI runner equivalent (Linux container)

### Benchmark Results

| Mode | Files Scanned | Wall Time | User CPU | System CPU | CPU % |
|------|---------------|-----------|----------|------------|-------|
| Full Scan | 1,998 | **2.63s** | 1.61s | 0.35s | 74% |
| Changed (1 file) | 1 | **1.18s** | 0.74s | 0.31s | 88% |
| Changed (10 files) | 10 | **0.47s** | 0.31s | 0.10s | 88% |

### Performance Analysis

#### Time Savings by PR Size

| PR Size | Typical Files | Full Scan | Changed-Files | Savings |
|---------|---------------|-----------|---------------|---------|
| Small (bug fix) | 1-5 files | 2.6s | 0.5-1.2s | **55-82%** |
| Medium (feature) | 5-20 files | 2.6s | 0.5-0.8s | **70-82%** |
| Large (refactor) | 50+ files | 2.6s | 1.0-1.5s | **42-62%** |

#### Scalability Considerations

The full scan time scales linearly with codebase size:
- **Current**: 1,998 files → 2.6s
- **Projected 3,000 files**: ~3.9s (50% growth)
- **Projected 5,000 files**: ~6.5s (150% growth)

Changed-files mode remains near-constant for typical PRs (~0.5-1.5s), making it increasingly valuable as the codebase grows.

#### ROI Assessment

At current scale, 2.6s is trivial compared to any non-toy test suite. The benefit is more about *perceived* responsiveness in PRs than hard CI budget savings. The long-term argument is the real justification: as omnibase_core grows into the 5k+ file range, the full scan cost will stop being noise.

**Decision point**: If growth will be slow, a simpler "always full scan, maybe optimize script internals" path is defensible.

#### Poetry Overhead

Note: ~0.3-0.5s of each run is Poetry virtual environment activation overhead, which is unavoidable regardless of mode.

---

## 2. Risk Assessment

### Risk Matrix

| Risk ID | Description | Severity | Likelihood | Overall | Mitigation |
|---------|-------------|----------|------------|---------|------------|
| RISK-001 | Pre-existing violations not detected after allowlist changes | HIGH | LOW | MEDIUM | Full scan on protected branch PRs |
| RISK-002 | Transitive import exposure | LOW | VERY LOW | NEGLIGIBLE | N/A (not detected by either mode) |
| RISK-003 | New banned modules not enforced on existing files | MEDIUM | LOW | LOW-MEDIUM | Process: full scan when script config changes |
| RISK-004 | Allowlist removals not validated | MEDIUM | LOW | LOW-MEDIUM | Process: require source file in same PR |
| RISK-005 | Git diff failures | VERY LOW | LOW | NEGLIGIBLE | Safe fallback to full scan (already implemented) |
| RISK-006 | Files outside src/omnibase_core | VERY LOW | VERY LOW | NEGLIGIBLE | By design - tests allowed |
| RISK-007 | Branch divergence race condition | LOW | LOW | LOW | Require rebase, full scan on merge |
| RISK-008 | Long-lived feature branches accumulate violations | LOW | MEDIUM | LOW-MEDIUM | Accepted - detected when PR targets protected branch |

### Risk Summary

**On protected branches**: No additional risk compared to current full scan.

**Accepted residual risks**:
- Long-lived feature branches that never target protected branches can accumulate violations for weeks before detection
- Configuration changes that accidentally disable full scan logic will silently degrade safety until noticed

### Mitigation Status

| Mitigation | Enforcement | Status |
|------------|-------------|--------|
| Full scan on protected branch PRs | CI workflow | **Enforced** |
| Full scan on push to main/develop | CI workflow | **Enforced** |
| Safe fallback on git errors | Script code | **Enforced** |
| Full scan when script config changes | Process/review | **Not enforced** (future enhancement) |
| Require source file for allowlist removals | Process/review | **Not enforced** (future enhancement) |

---

## 3. Implementation Options Comparison

| Option | PR CI Speed | Main Coverage | Complexity | Risk Level |
|--------|-------------|---------------|------------|------------|
| A: Always changed-files | Fast (0.5s) | Partial | Low | **HIGH** |
| B: Hybrid (changed PR, full main) | Fast (0.5s) | Full | Medium | Low-Medium |
| **B+: Enhanced Hybrid** | Fast (0.5s) | Full | Medium | Low (on protected branches) |
| C: Optimized full scan | Medium (1.5s) | Full | Medium | None |
| D: Smart hybrid + scheduled | Fast (0.5s) | Full | High | None |

### Recommended: Option B+ (Enhanced Hybrid)

**Why B+ over other options:**

- **vs Option A**: Option A has unacceptable risk of missing violations
- **vs Option B**: B+ catches violations before merge, not after
- **vs Option C**: B+ is faster with equivalent safety on protected branches
- **vs Option D**: B+ achieves same safety with less complexity

---

## 4. Implementation Plan

### Phase 1: Update CI Workflow

Replace the current transport check step in `.github/workflows/test.yml`:

**Current** (lines 268-270):
```yaml
- name: Check for transport import violations (OMN-220)
  run: |
    poetry run python scripts/check_transport_imports.py
```

**Updated**:
```yaml
- name: Check for transport import violations (OMN-220)
  id: transport-check
  run: |
    set +e  # Don't exit on first error, capture results

    # Determine what checks to run
    RUN_CHANGED_FILES="false"
    RUN_FULL_SCAN="false"

    if [[ "${{ github.event_name }}" == "pull_request" ]]; then
      if [[ "${{ github.base_ref }}" == "main" || "${{ github.base_ref }}" == "develop" ]]; then
        # PR to protected branch: full scan only (changed-files is redundant)
        RUN_FULL_SCAN="true"
        echo "=== Transport Import Check (Full Scan - PR to ${{ github.base_ref }}) ==="
      else
        # PR to non-protected branch: changed files only (fast feedback)
        RUN_CHANGED_FILES="true"
        echo "=== Transport Import Check (Changed Files - PR to ${{ github.base_ref }}) ==="
      fi
    elif [[ "${{ github.event_name }}" == "push" ]]; then
      # Only full scan on pushes to protected branches
      if [[ "${{ github.ref }}" == "refs/heads/main" || "${{ github.ref }}" == "refs/heads/develop" ]]; then
        RUN_FULL_SCAN="true"
        echo "=== Transport Import Check (Full Scan - Push to ${GITHUB_REF#refs/heads/}) ==="
      else
        # Push to non-protected branch: changed files only
        RUN_CHANGED_FILES="true"
        echo "=== Transport Import Check (Changed Files - Push to ${GITHUB_REF#refs/heads/}) ==="
      fi
    fi

    CHANGED_FILES_EXIT=0
    FULL_SCAN_EXIT=0

    if [[ "$RUN_CHANGED_FILES" == "true" ]]; then
      poetry run python scripts/check_transport_imports.py --changed-files --verbose
      CHANGED_FILES_EXIT=$?
    fi

    if [[ "$RUN_FULL_SCAN" == "true" ]]; then
      poetry run python scripts/check_transport_imports.py --verbose
      FULL_SCAN_EXIT=$?
    fi

    # Output for summary step
    echo "changed_files_exit=$CHANGED_FILES_EXIT" >> $GITHUB_OUTPUT
    echo "full_scan_exit=$FULL_SCAN_EXIT" >> $GITHUB_OUTPUT
    echo "run_changed_files=$RUN_CHANGED_FILES" >> $GITHUB_OUTPUT
    echo "run_full_scan=$RUN_FULL_SCAN" >> $GITHUB_OUTPUT

    # Restore strict mode
    set -e

    # Fail if any check found violations
    if [[ $CHANGED_FILES_EXIT -ne 0 ]] || [[ $FULL_SCAN_EXIT -ne 0 ]]; then
      echo ""
      echo "Transport import violations detected!"
      exit 1
    fi

    echo ""
    echo "All transport import checks passed."

- name: Transport check summary
  if: always()
  run: |
    echo "## Transport Import Validation (OMN-220)" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY

    RUN_CHANGED="${{ steps.transport-check.outputs.run_changed_files }}"
    RUN_FULL="${{ steps.transport-check.outputs.run_full_scan }}"
    CHANGED_EXIT="${{ steps.transport-check.outputs.changed_files_exit }}"
    FULL_EXIT="${{ steps.transport-check.outputs.full_scan_exit }}"

    if [[ "$RUN_CHANGED" == "true" ]]; then
      if [[ "$CHANGED_EXIT" == "0" ]]; then
        echo "- Changed files check: Passed" >> $GITHUB_STEP_SUMMARY
      else
        echo "- Changed files check: **Failed** (exit code: $CHANGED_EXIT)" >> $GITHUB_STEP_SUMMARY
      fi
    else
      echo "- Changed files check: Skipped (targeting protected branch)" >> $GITHUB_STEP_SUMMARY
    fi

    if [[ "$RUN_FULL" == "true" ]]; then
      if [[ "$FULL_EXIT" == "0" ]]; then
        echo "- Full scan: Passed" >> $GITHUB_STEP_SUMMARY
      else
        echo "- Full scan: **Failed** (exit code: $FULL_EXIT)" >> $GITHUB_STEP_SUMMARY
      fi
    else
      echo "- Full scan: Skipped (not targeting protected branch)" >> $GITHUB_STEP_SUMMARY
    fi
```

### Key Changes from Original Proposal

1. **Fixed branch conditions**: Push events now check `github.ref` to only full scan on main/develop
2. **Removed redundant work**: PRs to protected branches run full scan only (changed-files is redundant)
3. **Aligned comments with behavior**: Comments now accurately describe when each mode runs
4. **Restored `set -e`**: Strict mode restored after capturing exit codes

### Phase 2: Testing

1. Create PR with the updated workflow
2. Verify changed-files check runs for PRs to non-protected branches
3. Verify full scan runs for PRs to main/develop
4. Verify full scan runs for pushes to main/develop only
5. Verify summary output displays correctly

### Phase 3: Documentation

1. Update `DEPENDENCY_INVERSION.md` with the hybrid approach
2. Add section to CI_MONITORING_GUIDE.md about transport check behavior
3. Close Linear ticket OMN-651

---

## 5. Known Limitations

### `--changed-files` Compares to origin/main Only

The script's `--changed-files` mode always compares against `origin/main` or `origin/master`, not against `github.base_ref`.

**Impact**: For PRs targeting `develop`, if `develop` diverges significantly from `main`, the changed file detection may not be accurate.

**Example**: If a developer creates branch `feature/my-change` from `main` at commit `abc123`, then `main` advances to commit `def456`, the `--changed-files` mode will compare against `origin/main` (at `def456`), not the original branch point (`abc123`). This means:
- Files changed in `main` after branching may appear as "unchanged" in the diff
- Files that were the same at branch point but diverged in `main` may show as "changed"

In practice, this typically results in checking *more* files than strictly necessary (files touched by both the PR and recent main commits), which is a safe failure mode. The risk scenario is if a violation was introduced in `main` after branching and the PR happens to touch the same file - the violation would be detected, but attributed to the PR.

**Accepted for now**: The common case is PRs to `main`, and `develop` should be relatively close to `main`. A `--base-ref` argument can be added when this actually causes problems.

### Process Requirements (Not Enforced by CI)

The following mitigations are documentation-only and rely on code review discipline:

1. **Config changes**: When modifying `scripts/check_transport_imports.py` or its banned modules list, manually verify all existing files
2. **Allowlist removals**: When removing a file from `TEMPORARY_ALLOWLIST`, include the actual fix in the same PR

**Future enhancement**: Add path-based CI conditions to enforce these rules automatically.

---

## 6. Acceptance Criteria Checklist

- [x] Performance benchmarks documented
- [x] Risk analysis completed
- [x] Recommendation with justification
- [x] Implementation plan if proceeding
- [x] Review feedback incorporated (v1.1)

---

## 7. Appendix

### A. Script CLI Reference

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Enable verbose output with code snippets |
| `--file PATH`, `-f` | Check a specific file only |
| `--src-dir PATH` | Override source directory (default: `src/omnibase_core`) |
| `--json` | Output results as JSON |
| `--changed-files` | Only check files changed vs origin/main or origin/master |

### B. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No violations found |
| 1 | Transport import violations detected |
| 2 | Script error (invalid args, file not found) |

### C. Current Allowlist

```python
TEMPORARY_ALLOWLIST = {
    "mixins/mixin_health_check.py": "2026-06-10",  # Uses aiohttp directly
}
```

Note: Allowlist expiry is enforced by convention only. A future enhancement could add a scheduled CI job to flag expired entries.

### D. Banned Transport Modules

```python
BANNED_TRANSPORT_MODULES = {
    "kafka", "aiokafka", "confluent_kafka",
    "redis", "aioredis", "redis.asyncio",
    "httpx", "aiohttp", "requests",
    "asyncpg", "psycopg2", "psycopg",
    "motor", "pymongo",
    "aiobotocore", "boto3", "botocore",
    "grpc", "grpcio",
    "pika", "aio_pika",
    "nats", "nats.py",
    "websockets", "socketio",
}
```

---

## 8. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-10 | Initial evaluation |
| 1.1 | 2025-12-10 | Incorporated review feedback: fixed branch conditions, removed redundant work, demoted "zero risk" language, documented known limitations |

---

**Document Version**: 1.1
**Last Updated**: 2025-12-10
**Author**: Polymorphic Agent (OMN-651)
**Reviewer**: Human review feedback incorporated

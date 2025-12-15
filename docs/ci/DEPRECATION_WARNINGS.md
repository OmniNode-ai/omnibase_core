# Deprecation Warning Configuration

> **Linear Ticket**: OMN-199 - Configure pytest deprecation warning capture
> **Phase**: 7 - Deprecation & CI Enforcement
> **Last Updated**: 2025-12-13

---

## Overview

This document describes the deprecation warning strategy for omnibase_core, including the current configuration (v0.4.0) and the migration path to v0.5.0 where deprecation warnings will become test failures.

---

## Current State (v0.4.0)

### Configuration

In `pyproject.toml`, deprecation warnings are configured to display during test runs:

```toml
filterwarnings = [
    # === Deprecation Warning Capture (OMN-199, Phase 7) ===
    # Display deprecation warnings during test runs so developers can address them
    # before v0.5.0 when these will become errors
    "default::DeprecationWarning",
    "default::PendingDeprecationWarning",
]
```

### Behavior

- **DeprecationWarning**: Displayed during test runs (not failures)
- **PendingDeprecationWarning**: Displayed during test runs (not failures)
- **Developer Action**: Warnings should be addressed proactively before v0.5.0

### Why Display Instead of Error?

The `default` filter displays warnings without causing test failures. This allows:

1. **Visibility**: Developers see deprecation warnings in test output
2. **Gradual Migration**: Time to address warnings before they become blocking
3. **Non-Blocking CI**: Tests pass even with deprecation warnings during transition period

---

## v0.5.0 Migration Path

### Planned Configuration Change

In v0.5.0, the configuration will change from `default` to `error`:

```toml
filterwarnings = [
    # === Deprecation Warning Enforcement (v0.5.0) ===
    # Deprecation warnings are now errors - tests will fail if they trigger warnings
    "error::DeprecationWarning",
    "error::PendingDeprecationWarning",
]
```

### Impact

- **DeprecationWarning**: Will cause test failures
- **PendingDeprecationWarning**: Will cause test failures
- **CI Impact**: PRs with deprecation warnings will fail CI checks

### Timeline

| Version | Behavior | Action Required |
|---------|----------|-----------------|
| **v0.4.x** | Warnings displayed | Address warnings proactively |
| **v0.5.0** | Warnings become errors | All warnings must be resolved |

---

## How to Address Deprecation Warnings

### Step 1: Identify Warnings

Run the test suite and review deprecation warnings in the output:

```bash
# Run all tests and observe warnings
poetry run pytest tests/

# Run with verbose warnings
poetry run pytest tests/ -W default::DeprecationWarning
```

### Step 2: Categorize Warnings

Deprecation warnings typically fall into these categories:

| Category | Source | Resolution |
|----------|--------|------------|
| **Internal Code** | Your own deprecated usage | Update to new APIs |
| **Dependencies** | Third-party library deprecations | Update library or suppress |
| **Python stdlib** | Python version-specific deprecations | Update code patterns |

### Step 3: Resolve Internal Warnings

For warnings in omnibase_core code:

1. **Find the deprecated usage** in the warning message
2. **Check documentation** for the replacement API
3. **Update code** to use the non-deprecated alternative
4. **Verify fix** by re-running tests

Example:
```python
# Before (deprecated)
import warnings
warnings.warn("old_function is deprecated", DeprecationWarning)

# After (use new API)
from new_module import new_function
new_function()
```

### Step 4: Handle Dependency Warnings

For warnings from third-party libraries:

1. **Check if library update available** that resolves the warning
2. **Update dependency** if possible: `poetry update library-name`
3. **If no update available**, consider targeted suppression (see below)

### Step 5: Targeted Suppression (Last Resort)

If a warning cannot be resolved (e.g., waiting for upstream fix), add a targeted suppression:

```toml
# In pyproject.toml filterwarnings
filterwarnings = [
    "default::DeprecationWarning",
    "default::PendingDeprecationWarning",
    # Suppress specific unavoidable warning from dependency
    # TODO(YOUR-TICKET): Remove when library-name >= X.Y.Z
    "ignore:specific warning message:DeprecationWarning:library_name",
]
```

**Important**: Always include:
- A TODO comment with Linear ticket reference
- The minimum version that resolves the warning
- The specific warning message (not a broad suppression)

---

## Warning Filter Syntax Reference

### Filter Format

```text
action:message:category:module:line
```

### Actions

| Action | Effect |
|--------|--------|
| `error` | Turn warning into exception (test failure) |
| `ignore` | Suppress warning completely |
| `default` | Display warning once per location |
| `always` | Display warning every time |
| `once` | Display warning only first time |

### Examples

```toml
filterwarnings = [
    # Display all deprecation warnings (current v0.4.0 behavior)
    "default::DeprecationWarning",

    # Convert to errors (v0.5.0 behavior)
    "error::DeprecationWarning",

    # Suppress specific warning from specific module
    "ignore:datetime.datetime.utcnow:DeprecationWarning:some_library",

    # Suppress warnings matching regex pattern
    "ignore:.*is deprecated.*:DeprecationWarning",
]
```

---

## Pre-v0.5.0 Checklist

Before v0.5.0 release, ensure:

- [ ] Run full test suite: `poetry run pytest tests/`
- [ ] Review all `DeprecationWarning` output
- [ ] Update code to resolve internal deprecations
- [ ] Update dependencies where possible
- [ ] Add targeted suppressions for unavoidable warnings (with TODOs)
- [ ] Verify no new deprecation warnings appear

### Validation Command

```bash
# Temporarily treat deprecations as errors to validate readiness
poetry run pytest tests/ -W error::DeprecationWarning -W error::PendingDeprecationWarning
```

If this command passes, the codebase is ready for v0.5.0.

---

## Related Documentation

- [CI Monitoring Guide](CI_MONITORING_GUIDE.md) - CI health monitoring
- [CI Test Strategy](../testing/CI_TEST_STRATEGY.md) - Overall test strategy
- [Testing Guide](../guides/TESTING_GUIDE.md) - Comprehensive testing documentation

---

## Configuration Location

The warning filter configuration is located in:

```text
pyproject.toml
```

Under the `[tool.pytest.ini_options]` section, in the `filterwarnings` array.

---

**Last Updated**: 2025-12-13
**Document Version**: 1.0.0
**Linear Ticket**: OMN-199

> **Navigation**: [Home](../INDEX.md) > Testing > Testmon Usage Guide

# pytest-testmon Usage Guide

## Overview

pytest-testmon is an intelligent test selection tool that tracks code dependencies and runs only the tests affected by your changes. This dramatically speeds up local development and CI feedback loops.

## Quick Start

```bash
# Run only tests affected by recent changes
uv run pytest --testmon

# Reset testmon database and run all tests
uv run pytest --testmon-noselect

# Temporarily disable testmon
uv run pytest --testmon-off

# Run testmon with coverage on affected tests
uv run pytest --testmon --cov=src/omnibase_core --cov-report=term-missing
```

## How It Works

pytest-testmon:
1. **Tracks** which tests execute which source code files
2. **Detects** which source files have changed since last run
3. **Selects** only tests that depend on changed files
4. **Runs** the minimal test subset needed

**Database**: `.testmondata` (gitignored) stores test-to-code dependency mapping

## Use Cases

### Local Development (Recommended)

```bash
# Fast iteration: Run only affected tests
uv run pytest --testmon

# When testmon seems off, reset and rebuild
uv run pytest --testmon-noselect
```

**Speedup**: 10x-100x faster for small changes (12,198 tests → often <100 tests)

### Pre-Commit Validation

```bash
# Validate your changes before commit
uv run pytest --testmon --cov --cov-fail-under=60
```

### Full Suite (Periodic)

```bash
# Run full suite periodically to catch integration issues
uv run pytest tests/
```

## CI/CD Integration Strategy

See [CI_TEST_STRATEGY.md](./CI_TEST_STRATEGY.md) for recommended CI test approach.

## When Testmon May Miss Tests

- **Indirect dependencies**: Dynamic imports, reflection, metaprogramming
- **Configuration changes**: Changes to pytest.ini, conftest.py, fixtures
- **Data-driven tests**: External data files not tracked by testmon
- **Integration tests**: Complex multi-component interactions

**Mitigation**: Run full suite periodically (daily, before releases)

## Best Practices

1. **Use testmon for local development** (fast iteration)
2. **Reset testmon after major refactors** (rebuild dependency graph)
3. **Run full suite before pushing to main** (comprehensive validation)
4. **Check testmon selection** if unexpected test skips occur
5. **Don't rely solely on testmon for CI** (use as optimization, not replacement)

## Troubleshooting

### Testmon selecting too many/few tests

```bash
# Clear database and rebuild
rm .testmondata
uv run pytest --testmon-noselect
```

### Testmon not detecting changes

```bash
# Ensure you're using uv run
uv run pytest --testmon  # Correct
pytest --testmon              # Wrong (uses system pytest)
```

### Performance issues

```bash
# Testmon database may be corrupt
rm .testmondata
uv run pytest --testmon-noselect
```

## Performance Comparison

| Scenario | Full Suite | Testmon | Speedup |
|----------|-----------|---------|---------|
| 1 file changed | 12,198 tests | ~50 tests | ~244x |
| 5 files changed | 12,198 tests | ~200 tests | ~61x |
| 20 files changed | 12,198 tests | ~800 tests | ~15x |
| Major refactor | 12,198 tests | ~5,000 tests | ~2x |

**Note**: Speedups vary based on code coupling and test dependencies.

## Related Documentation

- [CI Test Strategy](./CI_TEST_STRATEGY.md) - Comprehensive CI/CD test approach
- [Testing Guide](../guides/TESTING_GUIDE.md) - Overall testing philosophy
- [pytest Documentation](https://docs.pytest.org/) - pytest reference

## Configuration

pytest-testmon configuration is minimal. See `pyproject.toml` [tool.pytest.ini_options] for usage examples.

**No additional configuration required** - testmon works out of the box with existing pytest configuration.

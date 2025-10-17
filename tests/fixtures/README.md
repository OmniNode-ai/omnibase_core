# Test Fixtures

This directory contains test fixtures using Pydantic bypass patterns for performance.

## ⚠️ WARNING: Test-Only Patterns

**NEVER use these patterns in production code (`src/`)**

The patterns in this directory bypass Pydantic validation for test performance. They are ONLY safe in test fixtures where data is known-valid by construction.

## Pydantic Bypass Pattern

### What is it?

Pydantic's `model_construct()` bypasses all validation, type coercion, and default value computation. This is dangerous in production but acceptable in tests for performance.

### Why Use It?

**Performance Benefits:**
- **Standard construction:** ~100-1000μs per model (with validation)
- **Bypass construction:** ~1-10μs per model (no validation)
- **Speedup:** 10-100x faster for large test suites

**When to use:**
- Creating thousands of test model instances
- Batch fixture generation for performance tests
- Test data known to be valid by construction

### Safety Guarantees

✅ **Enforced by pre-commit hook**
- Pre-commit hook: `no-pydantic-bypass-in-prod`
- Validation script: `scripts/validation/validate_no_pydantic_bypass.py`
- Blocks bypass patterns in `src/` directory
- Allows bypass patterns ONLY in `tests/`

✅ **Type safety maintained**
- Models still type-checked by mypy
- IDE autocomplete still works
- Type hints prevent most bugs

✅ **Integration tests validate real flows**
- Production code paths fully validated
- Test fixtures only used in unit tests
- Integration tests use real construction

## Usage

### 1. Inherit from TestFixtureBase

```python
from tests.fixtures.fixture_base import TestFixtureBase
from omnibase_core.models.your_model import YourModel

class YourFixtures(TestFixtureBase):
    """Fast test fixtures for YourModel."""

    @staticmethod
    def simple(**overrides) -> YourModel:
        """Create a simple test instance."""
        return TestFixtureBase.construct(
            YourModel,
            field1="value1",
            field2="value2",
            **overrides
        )
```

### 2. Use in Tests

```python
def test_your_function():
    # Fast fixture creation (no validation overhead)
    model = YourFixtures.simple(field1="custom_value")

    # Test your function
    result = your_function(model)

    # Assert results
    assert result.success
```

### 3. Batch Creation

```python
def test_batch_processing():
    # Create 100 instances efficiently (~1ms vs ~100ms)
    models = YourFixtures.many(
        count=100,
        field1="default_value",
        field2="default_value"
    )

    # Test batch processing
    results = process_batch(models)
    assert len(results) == 100
```

## Examples

### Simple Fixtures

See `fixture_context.py` for a minimal example:

```python
class ContextFixtures(TestFixtureBase):
    @staticmethod
    def simple(**overrides) -> ModelContext:
        return TestFixtureBase.construct(
            ModelContext,
            data={},
            **overrides
        )
```

### Complex Fixtures

See `fixture_error_context.py` for a more complex example with multiple factory methods:

```python
class ErrorContextFixtures(TestFixtureBase):
    @staticmethod
    def with_location(file_path: str = "test.py", **overrides):
        return TestFixtureBase.construct(
            ModelErrorContext,
            file_path=file_path,
            line_number=42,
            # ... other fields
            **overrides
        )
```

### Result Fixtures

See `fixture_result.py` for success/failure patterns:

```python
class ResultFixtures(TestFixtureBase):
    @staticmethod
    def success(**overrides) -> ModelBaseResult:
        return TestFixtureBase.construct(
            ModelBaseResult,
            exit_code=0,
            success=True,
            **overrides
        )
```

## Performance Comparison

| Operation | Standard | Bypass | Speedup |
|-----------|----------|--------|---------|
| Simple model (3 fields) | ~50μs | ~2μs | **25x** |
| Complex model (10+ fields) | ~200μs | ~5μs | **40x** |
| Nested models | ~500μs | ~10μs | **50x** |
| 100 instances | ~50ms | ~1ms | **50x** |

## What NOT to Do

### ❌ Don't use in production code

```python
# WRONG - This will be blocked by pre-commit hook
def create_user(name: str) -> User:
    return User.model_construct(name=name)  # ❌ BLOCKED
```

### ❌ Don't bypass validation for untrusted data

```python
# WRONG - Bypasses validation of external data
def parse_api_response(data: dict) -> Model:
    return Model.model_construct(**data)  # ❌ UNSAFE
```

### ❌ Don't use for complex validation logic

```python
# WRONG - Bypasses important business logic
def create_order(items: list) -> Order:
    return Order.model_construct(items=items)  # ❌ Missing validation
```

## What to Do Instead

### ✅ Use normal construction in production

```python
# CORRECT - Full validation
def create_user(name: str) -> User:
    return User(name=name)  # ✅ Validated
```

### ✅ Use TestFixtureBase in tests

```python
# CORRECT - Fast test fixtures
class UserFixtures(TestFixtureBase):
    @staticmethod
    def simple(**overrides) -> User:
        return TestFixtureBase.construct(
            User,
            name="test_user",
            **overrides
        )
```

### ✅ Validate at boundaries

```python
# CORRECT - Validate external data
def parse_api_response(data: dict) -> Model:
    return Model(**data)  # ✅ Full Pydantic validation
```

## Pre-Commit Hook Details

### Hook Configuration

`.pre-commit-config.yaml`:
```yaml
- id: no-pydantic-bypass-in-prod
  name: ONEX Pydantic Bypass Prevention
  entry: poetry run python scripts/validation/validate_no_pydantic_bypass.py
  language: system
  files: ^src/.*\.py$
  exclude: ^tests/.*$
```

### What it Checks

The hook detects these patterns in `src/`:
- `.model_construct(` - Bypasses validation
- `.__dict__[` - Direct dict manipulation
- `object.__setattr__(` - Bypasses frozen models

### What it Allows

These are NOT flagged:
- Comments: `# use model_construct for performance`
- Docstrings: `"""This uses model_construct()"""`
- String literals: `"model_construct"`
- Any code in `tests/` directory

### Testing the Hook

```bash
# Should pass (no violations in src/)
poetry run pre-commit run no-pydantic-bypass-in-prod --all-files

# Should fail if bypass patterns found in src/
echo "x = Model.model_construct()" > src/test_violation.py
poetry run pre-commit run no-pydantic-bypass-in-prod --files src/test_violation.py
```

## Migration Guide

### Migrating Existing Fixtures

If you have existing test fixtures using `model_construct()` directly:

**Before:**
```python
def create_test_user(**overrides):
    return User.model_construct(
        name="test",
        email="test@example.com",
        **overrides
    )
```

**After:**
```python
from tests.fixtures.fixture_base import TestFixtureBase

class UserFixtures(TestFixtureBase):
    @staticmethod
    def create_test_user(**overrides) -> User:
        return TestFixtureBase.construct(
            User,
            name="test",
            email="test@example.com",
            **overrides
        )
```

## Questions?

**Q: Can I use this in integration tests?**
A: Yes, but consider whether you need the performance. Integration tests often benefit from full validation to catch issues.

**Q: Will this break if Pydantic changes?**
A: `model_construct()` is part of Pydantic's public API and unlikely to break. If it does, we'll update TestFixtureBase.

**Q: What if I need custom validation logic?**
A: Use normal model construction in production code. Bypass patterns are ONLY for test fixtures with known-valid data.

**Q: How do I add more fixture types?**
A: Create a new file `fixture_<name>.py`, inherit from `TestFixtureBase`, and add factory methods.

## Related Documentation

- **ONEX Patterns:** `/Volumes/PRO-G40/Code/Archon/docs/ONEX_ARCHITECTURE_PATTERNS_COMPLETE.md`
- **PR #59 Follow-up Plan:** `docs/PR59_FOLLOWUP_PLAN.md` (Section 5)
- **Pre-commit Hooks:** `.pre-commit-config.yaml`
- **Validation Script:** `scripts/validation/validate_no_pydantic_bypass.py`

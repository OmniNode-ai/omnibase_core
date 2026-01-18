> **Navigation**: [Home](../index.md) > Guides > Custom Callable Patterns

# Custom Callable Patterns for Invariant Evaluation

**Purpose**: Guide to implementing and using custom callable validators with the Invariant Evaluation Service.

**Audience**: Developers implementing custom validation logic for output verification.

**Related**: [ServiceInvariantEvaluator](../../src/omnibase_core/services/invariant/service_invariant_evaluator.py)

---

## Overview

The `ServiceInvariantEvaluator` supports a `CUSTOM` invariant type that allows developers to define arbitrary validation logic through Python callables. This enables validation scenarios that cannot be expressed with the built-in invariant types (`SCHEMA`, `FIELD_PRESENCE`, `FIELD_VALUE`, `THRESHOLD`, `LATENCY`, `COST`).

Custom callables are dynamically imported and executed at evaluation time, providing flexibility while maintaining security through an optional allow-list mechanism.

---

## Callable Signatures

Custom callables **must** follow one of two signature patterns:

### Pattern 1: Boolean-only Return (Simple Validators)

```python
def my_validator(output: dict[str, Any], **kwargs) -> bool:
    """Simple validator returning pass/fail status.

    Args:
        output: The output dictionary to validate.
        **kwargs: Additional configuration from invariant config.

    Returns:
        True if validation passes, False otherwise.
    """
    return "required_field" in output
```

When using this pattern, the message is auto-generated:
- On pass: `"Custom validation passed"`
- On fail: `"Custom validation failed"`

### Pattern 2: Tuple Return with Message (Descriptive Validators)

```python
def my_validator(output: dict[str, Any], **kwargs) -> tuple[bool, str]:
    """Descriptive validator returning status and message.

    Args:
        output: The output dictionary to validate.
        **kwargs: Additional configuration from invariant config.

    Returns:
        Tuple of (passed: bool, message: str) for detailed feedback.
    """
    if "required_field" not in output:
        return (False, "Missing required_field in output")
    return (True, "All required fields present")
```

This pattern is **recommended** for production use as it provides meaningful feedback.

---

## Configuration Schema

The invariant configuration for `CUSTOM` type must contain:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `callable_path` | `str` | Yes | Fully qualified Python path to the validation function |
| `*` (any key) | `Any` | No | Additional keys are passed as `**kwargs` to the callable |

### Path Notation Formats

Two formats are supported:

```python
# Dot notation (standard Python module path)
"callable_path": "myapp.validators.check_output"

# Colon notation (entry point style, commonly used in setuptools)
"callable_path": "myapp.validators:check_output"
```

Both formats are equivalent and resolve to the same function.

---

## Usage Examples

### Example 1: Basic Boolean Validator

```python
# validators/status_check.py
from typing import Any

def has_valid_status(output: dict[str, Any], **kwargs) -> bool:
    """Check if output has a valid status."""
    return output.get("status") in ["success", "completed", "done"]
```

```python
# Usage
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)

evaluator = ServiceInvariantEvaluator()
invariant = ModelInvariant(
    name="status_check",
    type=EnumInvariantType.CUSTOM,
    severity=EnumSeverity.CRITICAL,
    config={"callable_path": "validators.status_check.has_valid_status"},
)

result = evaluator.evaluate(invariant, {"status": "success"})
assert result.passed is True
```

### Example 2: Validator with kwargs

```python
# validators/item_count.py
from typing import Any

def check_min_items(
    output: dict[str, Any],
    min_count: int = 1,
    field: str = "items",
    **kwargs
) -> tuple[bool, str]:
    """Check if output contains minimum number of items.

    Args:
        output: The output dictionary to validate.
        min_count: Minimum required item count (default: 1).
        field: Field name containing the items list (default: "items").
        **kwargs: Unused additional config.

    Returns:
        Tuple of (passed, message).
    """
    items = output.get(field, [])
    count = len(items) if isinstance(items, list) else 0

    if count >= min_count:
        return (True, f"Found {count} items (minimum: {min_count})")
    return (False, f"Only {count} items found, need at least {min_count}")
```

```python
# Usage - kwargs are passed from config
invariant = ModelInvariant(
    name="item_count_check",
    type=EnumInvariantType.CUSTOM,
    severity=EnumSeverity.WARNING,
    config={
        "callable_path": "validators.item_count:check_min_items",
        "min_count": 5,
        "field": "results"  # Check "results" field instead of default "items"
    },
)

result = evaluator.evaluate(invariant, {"results": [1, 2, 3]})
assert result.passed is False
assert "Only 3 items" in result.message
```

### Example 3: Complex Business Logic Validator

```python
# validators/api_response.py
from typing import Any

def validate_api_response(
    output: dict[str, Any],
    require_pagination: bool = False,
    allowed_statuses: list[str] | None = None,
    **kwargs
) -> tuple[bool, str]:
    """Validate API response structure and content.

    Args:
        output: The API response to validate.
        require_pagination: If True, response must include pagination info.
        allowed_statuses: List of valid status values (default: ["success"]).
        **kwargs: Unused additional config.

    Returns:
        Tuple of (passed, message).
    """
    errors = []
    allowed = allowed_statuses or ["success"]

    # Check required fields
    if "data" not in output:
        errors.append("Missing 'data' field")

    # Validate status
    status = output.get("status")
    if status not in allowed:
        errors.append(f"Invalid status: {status!r}, expected one of: {allowed}")

    # Check pagination if required
    if require_pagination:
        if "pagination" not in output:
            errors.append("Missing 'pagination' field")
        elif not isinstance(output.get("pagination"), dict):
            errors.append("'pagination' must be a dictionary")
        elif "total" not in output["pagination"]:
            errors.append("Pagination missing 'total' field")

    if errors:
        return (False, "; ".join(errors))
    return (True, "API response is valid")
```

```python
# Usage
invariant = ModelInvariant(
    name="api_response_validation",
    type=EnumInvariantType.CUSTOM,
    severity=EnumSeverity.CRITICAL,
    config={
        "callable_path": "validators.api_response:validate_api_response",
        "require_pagination": True,
        "allowed_statuses": ["success", "partial"]
    },
)

result = evaluator.evaluate(invariant, {
    "status": "success",
    "data": {"items": [1, 2, 3]},
    "pagination": {"total": 100, "page": 1}
})
assert result.passed is True
```

---

## Security Considerations

Custom callables involve **dynamic code execution**, which requires careful security consideration.

### Security Models

#### Trusted Code Model (Default)

When `allowed_import_paths=None` (default), any valid Python path is permitted:

```python
# ONLY use in fully trusted environments
evaluator = ServiceInvariantEvaluator()  # No allow-list
```

**Use only when**:
- All invariant configurations come from version-controlled, code-reviewed sources
- No external/user-provided configurations are evaluated
- The runtime environment is fully controlled

#### Restricted Model (Recommended for Production)

When `allowed_import_paths` is configured, only callables from specified module prefixes are allowed:

```python
# Production-recommended configuration
evaluator = ServiceInvariantEvaluator(
    allowed_import_paths=[
        "myapp.validators",         # All functions in myapp.validators
        "myapp.business_rules",     # All functions in myapp.business_rules
        "myapp.validators.core",    # Specific submodule
    ]
)
```

### Security Measures

The evaluator implements multiple security layers:

1. **Path Format Validation**: Only valid Python module paths are accepted. Malformed paths (containing invalid characters or injection attempts) are rejected before checking the allow-list.

2. **Empty Prefix Rejection**: Empty strings in the allow-list are ignored with a warning log, as they could match unintended paths.

3. **Prefix Format Validation**: Each allow-list prefix is validated to ensure it's a valid Python module path format.

4. **Strict Boundary Matching**: Uses exact segment boundaries (dot or colon) to prevent prefix bypass attacks:

   ```python
   # With allow-list = ["myapp.validators"]:
   "myapp.validators.check_output"      # ALLOWED (prefix + dot)
   "myapp.validators:check_output"      # ALLOWED (prefix + colon)
   "myapp.validators"                   # ALLOWED (exact match)
   "myapp.validators_evil.check"        # BLOCKED (no valid boundary)
   "myapp.validators_extended.check"    # BLOCKED (no valid boundary)
   "os.system"                          # BLOCKED (not in list)
   "builtins.eval"                      # BLOCKED (not in list)
   ```

5. **Defense-in-Depth Module Validation**: The parsed module path is validated separately from the full callable path.

6. **Callability Verification**: The resolved attribute is verified to be callable before invocation.

### Production Configuration Recommendations

```python
# Be specific about allowed modules
evaluator = ServiceInvariantEvaluator(
    allowed_import_paths=[
        "mycompany.app.validators",
        "mycompany.app.business_rules",
    ]
)

# Avoid overly broad prefixes like "mycompany" which would
# allow any module in your entire codebase
```

---

## Best Practices

### 1. Make Validators Stateless and Thread-Safe

Custom callables should not rely on module-level mutable state:

```python
# BAD: Module-level mutable state
_counter = 0

def counting_validator(output: dict, **kwargs) -> bool:
    global _counter
    _counter += 1  # NOT thread-safe!
    return output.get("count", 0) > _counter

# GOOD: Stateless validator
def counting_validator(output: dict, min_count: int = 1, **kwargs) -> bool:
    return output.get("count", 0) >= min_count
```

### 2. Accept **kwargs for Forward Compatibility

Always accept `**kwargs` even if not using additional parameters:

```python
# GOOD: Accepts future config additions
def my_validator(output: dict, **kwargs) -> bool:
    return "data" in output

# BAD: May break if new config keys are added
def my_validator(output: dict) -> bool:
    return "data" in output
```

### 3. Return Descriptive Messages

Use tuple return format with meaningful messages for debugging:

```python
# GOOD: Descriptive messages
def validate_response(output: dict, **kwargs) -> tuple[bool, str]:
    if "error" in output:
        return (False, f"Response contains error: {output['error']}")
    if not output.get("data"):
        return (False, "Response missing 'data' field")
    return (True, "Response structure is valid")

# LESS HELPFUL: Boolean only
def validate_response(output: dict, **kwargs) -> bool:
    return "error" not in output and output.get("data")
```

### 4. Handle Edge Cases Gracefully

Validators should handle unexpected input without raising exceptions:

```python
def safe_validator(output: dict, **kwargs) -> tuple[bool, str]:
    try:
        items = output.get("items", [])
        if not isinstance(items, list):
            return (False, f"Expected 'items' to be a list, got {type(items).__name__}")

        count = len(items)
        if count < 1:
            return (False, "No items found in output")

        return (True, f"Found {count} valid items")
    except Exception as e:
        # Should never reach here, but defensive
        return (False, f"Validation error: {type(e).__name__}: {e}")
```

### 5. Document Configuration Parameters

Use docstrings to document expected kwargs:

```python
def check_response_time(
    output: dict[str, Any],
    max_ms: float = 1000.0,
    warn_ms: float = 500.0,
    **kwargs
) -> tuple[bool, str]:
    """Check if response time is within acceptable limits.

    Configuration Parameters:
        max_ms: Maximum allowed response time in milliseconds.
                If exceeded, validation fails. Default: 1000.0
        warn_ms: Warning threshold in milliseconds.
                 If exceeded but under max_ms, passes with warning message.
                 Default: 500.0

    Expected Output Fields:
        response_time_ms: The response time to check (required).

    Returns:
        Tuple of (passed, message).
    """
    response_time = output.get("response_time_ms")
    if response_time is None:
        return (False, "Missing 'response_time_ms' in output")

    try:
        time_ms = float(response_time)
    except (TypeError, ValueError):
        return (False, f"Invalid response_time_ms: {response_time!r}")

    if time_ms > max_ms:
        return (False, f"Response time {time_ms}ms exceeds maximum {max_ms}ms")

    if time_ms > warn_ms:
        return (True, f"Response time {time_ms}ms is elevated (warning: >{warn_ms}ms)")

    return (True, f"Response time {time_ms}ms is acceptable")
```

### 6. Use Type Hints

Always use type hints for better tooling support and documentation:

```python
from typing import Any

def typed_validator(
    output: dict[str, Any],
    required_fields: list[str] | None = None,
    **kwargs: Any
) -> tuple[bool, str]:
    """Validate with proper type hints."""
    fields = required_fields or ["data"]
    missing = [f for f in fields if f not in output]
    if missing:
        return (False, f"Missing fields: {', '.join(missing)}")
    return (True, "All required fields present")
```

---

## Error Handling

The evaluator handles all errors gracefully without raising exceptions:

| Error Type | Handling | Result Message |
|------------|----------|----------------|
| Import error | Captured | `"Failed to import callable: {error}"` |
| Missing function | Captured | `"Failed to import callable: module has no attribute..."` |
| Not callable | Blocked | `"Resolved path is not callable: {path} (got {type})"` |
| Exception in callable | Captured | `"Custom callable raised exception: {type}: {error}"` |
| Invalid return type | Captured | `"Invalid custom callable return type: expected bool or (bool, str), got {type}"` |
| Path not in allow-list | Blocked | `"Callable path not in allowed list: {path}"` |

---

## Thread Safety

The `ServiceInvariantEvaluator` is **NOT thread-safe**. When using custom callables in a multi-threaded environment:

1. Create separate evaluator instances per thread
2. Use thread-local storage for evaluator instances
3. Ensure custom callables are stateless and thread-safe

```python
import threading

# Thread-local evaluator storage
_local = threading.local()

def get_evaluator() -> ServiceInvariantEvaluator:
    """Get thread-local evaluator instance."""
    if not hasattr(_local, "evaluator"):
        _local.evaluator = ServiceInvariantEvaluator(
            allowed_import_paths=["myapp.validators"]
        )
    return _local.evaluator
```

---

## Testing Custom Callables

Example test patterns for custom validators:

```python
import pytest
from omnibase_core.enums import EnumSeverity, EnumInvariantType
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.fixture
def evaluator() -> ServiceInvariantEvaluator:
    """Create evaluator for testing."""
    return ServiceInvariantEvaluator()


class TestMyCustomValidator:
    """Tests for custom validator."""

    def test_passes_with_valid_output(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Validator passes with valid output."""
        invariant = ModelInvariant(
            name="test_custom",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            config={
                "callable_path": "myapp.validators:my_validator",
                "min_count": 1
            },
        )

        result = evaluator.evaluate(invariant, {"items": [1, 2, 3]})

        assert result.passed is True
        assert "3 items" in result.message

    def test_fails_with_invalid_output(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Validator fails with invalid output."""
        invariant = ModelInvariant(
            name="test_custom",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.WARNING,
            config={
                "callable_path": "myapp.validators:my_validator",
                "min_count": 5
            },
        )

        result = evaluator.evaluate(invariant, {"items": [1, 2]})

        assert result.passed is False
        assert "need at least 5" in result.message
```

---

## Related Documentation

- [ServiceInvariantEvaluator Source](../../src/omnibase_core/services/invariant/service_invariant_evaluator.py) - Full implementation with inline docs
- [Test Examples](../../tests/unit/services/invariant/custom_validators.py) - Sample validators used in tests
- [Threading Guide](THREADING.md) - Thread safety patterns
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns

---

**Last Updated**: 2026-01-03
**Documentation Version**: 1.0.0
**Framework Version**: omnibase_core 0.4.0+

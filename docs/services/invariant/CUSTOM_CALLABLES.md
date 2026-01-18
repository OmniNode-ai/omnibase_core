> **Navigation**: [Home](../../index.md) > [Services](../README.md) > Invariant > Custom Callables

# Custom Callable Invariants Guide

This guide documents the custom callable pattern for the `ServiceInvariantEvaluator`, which allows users to define arbitrary validation logic through Python functions.

## Overview

The `CUSTOM` invariant type enables dynamic validation by importing and executing user-defined Python functions at runtime. This provides maximum flexibility for validation scenarios that cannot be expressed with built-in invariant types.

## When to Use Custom Callables

Use custom callables when:

- Built-in invariants (`SCHEMA`, `FIELD_PRESENCE`, `FIELD_VALUE`, `THRESHOLD`, `LATENCY`, `COST`) don't meet your needs
- You need complex business logic validation
- Validation requires external data or calculations
- You need cross-field validation within the output

**Prefer built-in invariants when possible** - they are more secure, faster, and require no additional code.

## Callable Signature

Custom callables must follow one of two signature patterns:

### Pattern 1: Boolean Return (Simple)

```python
from typing import Any

def my_validator(output: dict[str, Any], **kwargs) -> bool:
    """Simple validator returning True/False."""
    return "required_field" in output
```

When using this pattern, the evaluator generates a default message:
- Pass: `"Custom validation passed"`
- Fail: `"Custom validation failed"`

### Pattern 2: Tuple Return (Descriptive)

```python
from typing import Any

def my_validator(output: dict[str, Any], **kwargs) -> tuple[bool, str]:
    """Descriptive validator with custom message."""
    if "required_field" not in output:
        return (False, "Missing required_field")
    return (True, "All required fields present")
```

This pattern provides detailed feedback in the validation result message.

## Configuration

### Required Configuration

```python
config = {
    "callable_path": "module.submodule.function_name"  # Required
}
```

### Callable Path Formats

Two notation formats are supported:

| Format | Example | Description |
|--------|---------|-------------|
| Dot notation | `"myapp.validators.check_output"` | Standard Python import path |
| Colon notation | `"myapp.validators:check_output"` | Entry point style (setuptools) |

Both formats are equivalent; choose based on your project conventions.

### Passing Arguments to Callables

Any additional keys in the config dictionary are passed as keyword arguments:

```python
# Config
config = {
    "callable_path": "myapp.validators:check_min_items",
    "min_count": 5,
    "field": "results"
}

# Callable receives min_count=5, field="results" as kwargs
def check_min_items(
    output: dict,
    min_count: int = 1,
    field: str = "items",
    **kwargs
) -> tuple[bool, str]:
    items = output.get(field, [])
    count = len(items) if isinstance(items, list) else 0
    if count >= min_count:
        return (True, f"Found {count} items (min: {min_count})")
    return (False, f"Only {count} items, need at least {min_count}")
```

## Complete Example

### 1. Define Your Validator

```python
# myapp/validators/api_validators.py

from typing import Any


def validate_api_response(
    output: dict[str, Any],
    require_pagination: bool = False,
    min_items: int = 0,
    **kwargs
) -> tuple[bool, str]:
    """Validate API response structure and content.

    Args:
        output: The API response to validate.
        require_pagination: Whether pagination info is required.
        min_items: Minimum number of items in data array.
        **kwargs: Additional arguments (ignored).

    Returns:
        Tuple of (passed, message).
    """
    errors = []

    # Check required fields
    if "data" not in output:
        errors.append("Missing 'data' field")
    elif isinstance(output["data"], list):
        if len(output["data"]) < min_items:
            errors.append(f"Expected at least {min_items} items, got {len(output['data'])}")

    # Check pagination if required
    if require_pagination:
        if "pagination" not in output:
            errors.append("Missing 'pagination' field")
        elif not output["pagination"].get("total"):
            errors.append("Pagination missing 'total'")

    if errors:
        return (False, "; ".join(errors))
    return (True, "API response is valid")
```

### 2. Configure the Invariant

```python
from omnibase_core.enums import EnumSeverity, EnumInvariantType
from omnibase_core.models.invariant import ModelInvariant

invariant = ModelInvariant(
    name="api_response_check",
    type=EnumInvariantType.CUSTOM,
    severity=EnumSeverity.CRITICAL,
    config={
        "callable_path": "myapp.validators.api_validators:validate_api_response",
        "require_pagination": True,
        "min_items": 1,
    },
)
```

### 3. Evaluate

```python
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)

evaluator = ServiceInvariantEvaluator()

# Valid response
output = {
    "data": [{"id": 1}, {"id": 2}],
    "pagination": {"total": 100, "page": 1},
}
result = evaluator.evaluate(invariant, output)
print(result.passed)  # True
print(result.message)  # "API response is valid"

# Invalid response
output = {"data": []}
result = evaluator.evaluate(invariant, output)
print(result.passed)  # False
print(result.message)  # "Expected at least 1 items, got 0; Missing 'pagination' field"
```

## Security Model

Custom callables involve dynamic code execution, which requires security consideration.

### Trusted Code Model (Default)

When `allowed_import_paths=None` (the default), any valid Python module path is permitted:

```python
# All valid Python paths are allowed
evaluator = ServiceInvariantEvaluator()
```

**Use only when all invariant configurations come from trusted sources** (e.g., version-controlled config files, internal APIs).

### Restricted Model (Recommended for Production)

Configure an allow-list to restrict which modules can be imported:

```python
evaluator = ServiceInvariantEvaluator(
    allowed_import_paths=[
        "myapp.validators",
        "myapp.business_rules",
    ]
)
```

#### Allow-List Matching Rules

The evaluator uses **strict boundary matching** to prevent bypass attacks:

| Callable Path | Allow-List Entry | Allowed? | Reason |
|---------------|------------------|----------|--------|
| `myapp.validators.check` | `myapp.validators` | Yes | Prefix + dot |
| `myapp.validators:check` | `myapp.validators` | Yes | Prefix + colon |
| `myapp.validators` | `myapp.validators` | Yes | Exact match |
| `myapp.validators_evil.check` | `myapp.validators` | **No** | No boundary |
| `os.system` | `myapp.validators` | **No** | Not in list |

#### Security Measures

1. **Path Format Validation**: Only valid Python module paths are accepted (letters, digits, underscores, dots, colon).

2. **Empty Prefix Rejection**: Empty strings in the allow-list are ignored with a warning.

3. **Prefix Format Validation**: Each allow-list prefix is validated before use.

4. **Strict Boundary Matching**: Requires a dot or colon separator to prevent prefix bypass attacks.

### Production Configuration Example

```python
# Be specific about allowed modules
evaluator = ServiceInvariantEvaluator(
    allowed_import_paths=[
        "mycompany.app.validators",
        "mycompany.app.business_rules",
        # Avoid overly broad prefixes like "mycompany"
    ]
)
```

## Error Handling

The evaluator captures all errors and returns them as failed validation results:

| Error Type | Result |
|------------|--------|
| Import error | `(False, "Failed to import callable: {error}", None, callable_path)` |
| Missing function | `(False, "Failed to import callable: {AttributeError}", None, callable_path)` |
| Exception in callable | `(False, "Custom callable raised exception: {type}: {error}", None, callable_path)` |
| Invalid return type | `(False, "Invalid custom callable return type: ...", result, callable_path)` |
| Path not allowed | `(False, "Callable path not in allowed list: {path}", None, callable_path)` |

## Thread Safety

Custom callables **should be stateless and thread-safe**:

```python
# GOOD: Stateless validator
def check_status(output: dict, **kwargs) -> bool:
    return output.get("status") == "success"

# BAD: Uses mutable module-level state
_counter = 0
def check_with_counter(output: dict, **kwargs) -> bool:
    global _counter
    _counter += 1  # Not thread-safe!
    return True
```

If state is required:
- Use thread-local storage
- Pass configuration via kwargs
- Use the output dictionary itself

## Best Practices

### 1. Always Accept `**kwargs`

Include `**kwargs` in your signature to handle future configuration additions:

```python
def my_validator(output: dict, required_field: str = "data", **kwargs) -> bool:
    return required_field in output
```

### 2. Return Descriptive Messages

Use the tuple return pattern for better debugging:

```python
def check_status(output: dict, **kwargs) -> tuple[bool, str]:
    status = output.get("status")
    if status == "success":
        return (True, f"Status is '{status}'")
    return (False, f"Expected status 'success', got '{status}'")
```

### 3. Handle Missing Fields Gracefully

Don't assume fields exist; use `.get()` with defaults:

```python
def check_count(output: dict, min_count: int = 1, **kwargs) -> tuple[bool, str]:
    count = output.get("count", 0)  # Default to 0 if missing
    if count >= min_count:
        return (True, f"Count {count} >= {min_count}")
    return (False, f"Count {count} < {min_count}")
```

### 4. Keep Validators Focused

Each validator should check one concern:

```python
# GOOD: Single responsibility
def check_has_data(output: dict, **kwargs) -> bool:
    return "data" in output

def check_data_not_empty(output: dict, **kwargs) -> bool:
    data = output.get("data", [])
    return len(data) > 0

# BAD: Multiple concerns
def check_everything(output: dict, **kwargs) -> bool:
    return ("data" in output and
            len(output["data"]) > 0 and
            output.get("status") == "success" and
            output.get("latency", 999) < 100)
```

### 5. Document Your Validators

Include docstrings explaining arguments and validation logic:

```python
def validate_response(
    output: dict,
    max_latency_ms: int = 500,
    require_data: bool = True,
    **kwargs
) -> tuple[bool, str]:
    """Validate API response meets requirements.

    Args:
        output: The API response dictionary.
        max_latency_ms: Maximum acceptable latency in milliseconds.
        require_data: Whether the 'data' field is required.
        **kwargs: Additional arguments (ignored).

    Returns:
        Tuple of (passed, message).
    """
    # Implementation...
```

## Using with ModelCustomInvariantConfig

For type-safe configuration, use `ModelCustomInvariantConfig`:

```python
from omnibase_core.models.invariant import ModelCustomInvariantConfig

# This validates the callable_path format at creation time
config = ModelCustomInvariantConfig(
    callable_path="myapp.validators.check_output",
    kwargs={"threshold": 100}
)

# Access properties
print(config.callable_path)  # "myapp.validators.check_output"
print(config.kwargs)         # {"threshold": 100}
```

## Related Documentation

- [ServiceInvariantEvaluator](../../../src/omnibase_core/services/invariant/service_invariant_evaluator.py) - Main evaluator class
- [ModelCustomInvariantConfig](../../../src/omnibase_core/models/invariant/model_custom_invariant_config.py) - Configuration model
- [Invariant Models](../../../src/omnibase_core/models/invariant/) - All invariant-related models

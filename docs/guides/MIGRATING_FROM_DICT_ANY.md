# Migrating from dict[str, Any] to Typed Models

**Version**: 0.4.0
**Last Updated**: 2025-12-25
**Correlation ID**: `dict-any-migration-001`

> **Type Safety Enhancement**: This guide covers the migration from untyped `dict[str, Any]` patterns to strongly-typed Pydantic models introduced in PR #240.

## Table of Contents

1. [Overview](#overview)
2. [Why Migrate?](#why-migrate)
3. [New Typed Models](#new-typed-models)
4. [Migration Guide: ModelErrorDetails](#migration-guide-modelerrordetails)
5. [Migration Guide: ModelEffectOperationConfig](#migration-guide-modeleffectoperationconfig)
6. [Migration Guide: ModelSchemaValue](#migration-guide-modelschemavalue)
7. [Backward Compatibility](#backward-compatibility)
8. [Common Migration Patterns](#common-migration-patterns)
9. [Testing Your Migration](#testing-your-migration)
10. [Troubleshooting](#troubleshooting)

---

## Overview

ONEX has replaced `dict[str, Any]` usage in key interfaces with strongly-typed Pydantic models. This improves:

- **Type safety**: Catch errors at development time, not runtime
- **IDE support**: Better autocomplete and documentation
- **Validation**: Automatic field validation via Pydantic
- **Documentation**: Self-documenting field names and types

### What Changed?

| Context | Before | After |
|---------|--------|-------|
| Error details | `dict[str, Any]` | `ModelErrorDetails` |
| Effect operation config | `dict[str, Any]` | `ModelEffectOperationConfig` |
| Arbitrary schema values | `Any` | `ModelSchemaValue` |

---

## Why Migrate?

### Problems with dict[str, Any]

```python
# BEFORE: No type safety
def handle_error(details: dict[str, Any]) -> None:
    code = details.get("code")  # Could be None, str, int - unknown!
    message = details.get("msg")  # Typo: should be "message"
    # Runtime error when 'message' is missing
```

### Benefits of Typed Models

```python
# AFTER: Full type safety
from omnibase_core.models.services import ModelErrorDetails

def handle_error(details: ModelErrorDetails) -> None:
    code = details.error_code  # Always str, IDE knows the type
    message = details.error_message  # Correct field name, autocomplete works
    # Pydantic validates all fields at construction
```

---

## New Typed Models

### ModelErrorDetails

**Location**: `omnibase_core.models.services.model_error_details`

**Purpose**: Replaces `dict[str, Any]` for error context and details.

**Key Features**:
- Required fields: `error_code`, `error_type`, `error_message`
- Optional tracking: `request_id`, `user_id`, `session_id`
- Recovery hints: `retry_after_seconds`, `recovery_suggestions`
- Nested errors: `inner_errors` for error chains
- Immutable (frozen=True) for thread safety

### ModelEffectOperationConfig

**Location**: `omnibase_core.models.operations.model_effect_operation_config`

**Purpose**: Replaces `dict[str, Any]` for effect operation configuration.

**Key Features**:
- Typed IO configurations via discriminated union
- Supports HTTP, DB, Kafka, and Filesystem handlers
- Retry policy and circuit breaker configuration
- Immutable (frozen=True) for thread safety

### ModelSchemaValue

**Location**: `omnibase_core.models.common.model_schema_value`

**Purpose**: Replaces `Any` for arbitrary JSON-compatible values.

**Key Features**:
- Type-tagged union (string, number, boolean, null, array, object)
- Factory methods: `from_value()`, `create_string()`, etc.
- Type checking: `is_string()`, `is_number()`, etc.
- Value extraction: `get_string()`, `get_number()`, etc.

---

## Migration Guide: ModelErrorDetails

### Before (dict[str, Any])

```python
from typing import Any

def create_error_context() -> dict[str, Any]:
    return {
        "code": "VALIDATION_ERROR",
        "message": "Invalid email format",
        "field": "user_email",
    }

def log_error(details: dict[str, Any]) -> None:
    print(f"Error: {details.get('code')} - {details.get('message')}")
```

### After (ModelErrorDetails)

```python
from omnibase_core.models.services import ModelErrorDetails
from omnibase_core.models.common import ModelSchemaValue

def create_error_context() -> ModelErrorDetails:
    return ModelErrorDetails(
        error_code="VALIDATION_ERROR",
        error_type="validation",
        error_message="Invalid email format",
        context_data={
            "field": ModelSchemaValue.create_string("user_email"),
        },
    )

def log_error(details: ModelErrorDetails) -> None:
    print(f"Error: {details.error_code} - {details.error_message}")
```

### Using from_dict() for Gradual Migration

If you have existing dict data, use the `from_dict()` factory:

```python
# Existing legacy code returns dict
legacy_data = {
    "code": "ERR_001",  # Legacy field name
    "message": "Something failed",  # Legacy field name
}

# Convert to typed model with automatic field mapping
error = ModelErrorDetails.from_dict(legacy_data)
assert error.error_code == "ERR_001"  # Mapped from 'code'
assert error.error_message == "Something failed"  # Mapped from 'message'
assert error.error_type == "runtime"  # Default value
```

### Migration Steps

1. **Import the model**:
   ```python
   from omnibase_core.models.services import ModelErrorDetails
   ```

2. **Update function signatures**:
   ```python
   # Before
   def process_error(details: dict[str, Any]) -> None: ...

   # After
   def process_error(details: ModelErrorDetails) -> None: ...
   ```

3. **Create typed instances**:
   ```python
   error = ModelErrorDetails(
       error_code="VALIDATION_ERROR",
       error_type="validation",
       error_message="Invalid input",
   )
   ```

4. **Access fields directly**:
   ```python
   # Before
   code = details.get("error_code", "UNKNOWN")

   # After
   code = error.error_code
   ```

---

## Migration Guide: ModelEffectOperationConfig

### Before (dict[str, Any])

```python
from typing import Any

def execute_http_call(config: dict[str, Any]) -> None:
    url = config.get("url")
    method = config.get("method", "GET")
    timeout = config.get("timeout_ms", 30000)
```

### After (ModelEffectOperationConfig)

```python
from omnibase_core.models.operations import ModelEffectOperationConfig
from omnibase_core.models.contracts.subcontracts import ModelHttpIOConfig

def execute_http_call(config: ModelEffectOperationConfig) -> None:
    io = config.get_typed_io_config()
    if isinstance(io, ModelHttpIOConfig):
        url = io.url_template
        method = io.method
    timeout = config.operation_timeout_ms or 30000
```

### Creating Configuration

```python
# Direct creation with typed IO config
config = ModelEffectOperationConfig(
    io_config=ModelHttpIOConfig(
        handler_type="http",
        url_template="https://api.example.com/users/${input.user_id}",
        method="GET",
    ),
    operation_name="fetch_user",
    operation_timeout_ms=5000,
)

# Or from dict (for migration)
config = ModelEffectOperationConfig.from_dict({
    "io_config": {
        "handler_type": "http",
        "url_template": "https://api.example.com/users/123",
        "method": "GET",
    },
    "operation_name": "fetch_user",
})
```

### Migration Steps

1. **Import the model**:
   ```python
   from omnibase_core.models.operations import ModelEffectOperationConfig
   from omnibase_core.models.contracts.subcontracts import (
       ModelHttpIOConfig,
       ModelDbIOConfig,
       ModelKafkaIOConfig,
       ModelFilesystemIOConfig,
   )
   ```

2. **Update function signatures**:
   ```python
   # Before
   async def execute_operation(config: dict[str, Any]) -> Any: ...

   # After
   async def execute_operation(config: ModelEffectOperationConfig) -> Any: ...
   ```

3. **Use typed accessors**:
   ```python
   # Get typed IO config with automatic parsing
   io_config = config.get_typed_io_config()

   # Get response handling as dict (for legacy code)
   response_cfg = config.get_response_handling_as_dict()
   ```

---

## Migration Guide: ModelSchemaValue

### Before (Any)

```python
from typing import Any

def store_metadata(key: str, value: Any) -> None:
    # No type safety, anything goes
    cache[key] = value

def get_metadata(key: str) -> Any:
    return cache.get(key)
```

### After (ModelSchemaValue)

```python
from omnibase_core.models.common import ModelSchemaValue

def store_metadata(key: str, value: ModelSchemaValue) -> None:
    cache[key] = value

def get_metadata(key: str) -> ModelSchemaValue | None:
    return cache.get(key)
```

### Creating Values

```python
# From Python values (auto-detection)
str_val = ModelSchemaValue.from_value("hello")
num_val = ModelSchemaValue.from_value(42)
bool_val = ModelSchemaValue.from_value(True)
list_val = ModelSchemaValue.from_value([1, 2, 3])
dict_val = ModelSchemaValue.from_value({"key": "value"})

# Using factory methods (explicit)
str_val = ModelSchemaValue.create_string("hello")
num_val = ModelSchemaValue.create_number(42)
bool_val = ModelSchemaValue.create_boolean(True)
null_val = ModelSchemaValue.create_null()
```

### Type Checking and Access

```python
value = ModelSchemaValue.from_value("hello")

# Type checking
if value.is_string():
    text = value.get_string()  # Returns str
elif value.is_number():
    num = value.get_number()  # Returns ModelNumericValue
elif value.is_array():
    items = value.get_array()  # Returns list[ModelSchemaValue]

# Convert back to Python value
python_value = value.to_value()
```

### Migration Steps

1. **Import the model**:
   ```python
   from omnibase_core.models.common import ModelSchemaValue
   ```

2. **Update type annotations**:
   ```python
   # Before
   metadata: dict[str, Any] = {}

   # After
   metadata: dict[str, ModelSchemaValue] = {}
   ```

3. **Wrap values on storage**:
   ```python
   # Before
   metadata["count"] = 42

   # After
   metadata["count"] = ModelSchemaValue.from_value(42)
   ```

4. **Unwrap values on retrieval**:
   ```python
   # Before
   count = metadata.get("count", 0)

   # After
   count_val = metadata.get("count")
   count = count_val.to_value() if count_val else 0
   ```

---

## Backward Compatibility

### from_dict() Methods

All new models provide `from_dict()` factory methods for gradual migration:

```python
# ModelErrorDetails
error = ModelErrorDetails.from_dict({"code": "ERR", "message": "Failed"})

# ModelEffectOperationConfig
config = ModelEffectOperationConfig.from_dict({
    "io_config": {"handler_type": "http", ...},
})
```

### from_value() for ModelSchemaValue

```python
# Convert any Python value
value = ModelSchemaValue.from_value(existing_python_value)
```

### Legacy Field Mappings

ModelErrorDetails handles common legacy field names:

| Legacy Field | Maps To |
|--------------|---------|
| `code` | `error_code` |
| `message` | `error_message` |
| (missing) | `error_type` defaults to `"runtime"` |

---

## Common Migration Patterns

### Pattern 1: Returning Typed Errors

```python
# Before
def validate_user(data: dict) -> dict[str, Any] | None:
    if not data.get("email"):
        return {"code": "MISSING_EMAIL", "message": "Email required"}
    return None

# After
def validate_user(data: dict) -> ModelErrorDetails | None:
    if not data.get("email"):
        return ModelErrorDetails(
            error_code="MISSING_EMAIL",
            error_type="validation",
            error_message="Email required",
            component="UserValidator",
        )
    return None
```

### Pattern 2: Structured Error Details

When you need structured, type-safe error details (e.g., for API responses,
error aggregation, or detailed logging), use `ModelErrorDetails` directly:

```python
# Before - untyped dict for error context
from typing import Any

def validate_and_report(data: dict) -> dict[str, Any] | None:
    if not data.get("email"):
        return {"field": "email", "reason": "invalid format"}
    return None

# After - typed ModelErrorDetails with context_data
from omnibase_core.models.services import ModelErrorDetails
from omnibase_core.models.common import ModelSchemaValue

def validate_and_report(data: dict) -> ModelErrorDetails | None:
    if not data.get("email"):
        return ModelErrorDetails(
            error_code="VALIDATION_ERROR",
            error_type="validation",
            error_message="Invalid email format",
            context_data={
                "field": ModelSchemaValue.create_string("email"),
                "reason": ModelSchemaValue.create_string("invalid format"),
            },
        )
    return None
```

For exception context, `ModelOnexError` accepts keyword arguments directly:

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums import EnumCoreErrorCode

# Simple context via keyword arguments
raise ModelOnexError(
    message="Validation failed",
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    field="email",
    reason="invalid format",
)
```

### Pattern 3: Effect Configuration

```python
# Before
from typing import Any

async def call_api(config: dict[str, Any]) -> dict[str, Any]:
    url = config["url"]
    method = config.get("method", "GET")
    ...

# After
from typing import Any

from omnibase_core.models.operations import ModelEffectOperationConfig
from omnibase_core.models.contracts.subcontracts import ModelHttpIOConfig

async def call_api(config: ModelEffectOperationConfig) -> dict[str, Any]:
    io = config.get_typed_io_config()
    if not isinstance(io, ModelHttpIOConfig):
        raise ValueError("Expected HTTP config")
    url = io.url_template
    method = io.method
    ...
```

### Pattern 4: Metadata Storage

```python
# Before
node_metadata: dict[str, Any] = {
    "version": "1.0.0",
    "enabled": True,
    "max_retries": 3,
}

# After
node_metadata: dict[str, ModelSchemaValue] = {
    "version": ModelSchemaValue.create_string("1.0.0"),
    "enabled": ModelSchemaValue.create_boolean(True),
    "max_retries": ModelSchemaValue.create_number(3),
}
```

---

## Testing Your Migration

### Unit Tests

```python
import pytest
from omnibase_core.models.services import ModelErrorDetails
from omnibase_core.models.common import ModelSchemaValue

def test_error_details_creation():
    error = ModelErrorDetails(
        error_code="TEST_ERROR",
        error_type="runtime",
        error_message="Test message",
    )
    assert error.error_code == "TEST_ERROR"
    assert error.is_retryable() is False

def test_error_details_from_dict_legacy():
    # Test legacy field mapping
    error = ModelErrorDetails.from_dict({
        "code": "LEGACY_CODE",
        "message": "Legacy message",
    })
    assert error.error_code == "LEGACY_CODE"
    assert error.error_message == "Legacy message"
    assert error.error_type == "runtime"

def test_schema_value_round_trip():
    original = {"nested": [1, 2, 3], "flag": True}
    value = ModelSchemaValue.from_value(original)
    restored = value.to_value()
    assert restored == original
```

### Type Checking

Run mypy to verify type correctness:

```bash
poetry run mypy src/omnibase_core/
```

---

## Troubleshooting

### Issue 1: ValidationError on Creation

**Cause**: Required fields missing.

```python
# WRONG - missing required fields
error = ModelErrorDetails()

# CORRECT - provide required fields
error = ModelErrorDetails(
    error_code="ERR",
    error_type="runtime",
    error_message="Description",
)
```

### Issue 2: Frozen Instance Error

**Cause**: Trying to modify immutable model.

```python
error = ModelErrorDetails(...)
error.error_code = "NEW"  # ERROR: frozen instance

# CORRECT: Create new instance
new_error = error.model_copy(update={"error_code": "NEW"})
```

### Issue 3: ModelSchemaValue Type Mismatch

**Cause**: Accessing wrong value type.

```python
value = ModelSchemaValue.from_value("hello")
num = value.get_number()  # ERROR: Expected numeric value, got string

# CORRECT: Check type first
if value.is_number():
    num = value.get_number()
```

### Issue 4: from_dict Modifies Original

**Cause**: `from_dict()` modifies the input dict.

```python
original = {"code": "ERR", "message": "msg"}
error = ModelErrorDetails.from_dict(original)
# 'original' has been modified!

# CORRECT: Pass a copy
error = ModelErrorDetails.from_dict(original.copy())
```

---

## Additional Resources

- **ModelErrorDetails**: `src/omnibase_core/models/services/model_error_details.py`
- **ModelEffectOperationConfig**: `src/omnibase_core/models/operations/model_effect_operation_config.py`
- **ModelSchemaValue**: `src/omnibase_core/models/common/model_schema_value.py`
- **Error Handling Guide**: `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`
- **Threading Guide**: `docs/guides/THREADING.md`

---

**Last Updated**: 2025-12-25
**Version**: 0.4.0
**Maintainer**: ONEX Framework Team

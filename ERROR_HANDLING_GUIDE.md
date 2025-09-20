# ONEX Error Handling Guide

## Overview

This document provides comprehensive guidance on error handling patterns used throughout the ONEX framework. It consolidates best practices, usage examples, and guidelines for when to use each error handling approach.

## Error Handling Architecture

### 1. Standard Exception Hierarchy

The ONEX framework uses a structured exception hierarchy:

```
Exception
├── OnexError (Base ONEX error with error codes)
├── ValidationFrameworkError (Base validation error)
│   ├── ConfigurationError
│   ├── FileProcessingError
│   │   └── ProtocolParsingError
│   ├── AuditError
│   ├── MigrationError
│   ├── InputValidationError
│   └── PathTraversalError
└── Pydantic ValidationError (Built-in validation)
```

### 2. Error Handling Patterns

#### Pattern 1: OnexError with Error Codes
**When to Use:** Core framework operations, service-level errors
**Location:** `src/omnibase_core/exceptions/base_onex_error.py`

```python
from omnibase_core.exceptions.base_onex_error import OnexError
from omnibase_core.core.errors.core_errors import CoreErrorCode

# Example usage
try:
    result = risky_operation()
except FileNotFoundError as e:
    raise OnexError(
        code=CoreErrorCode.FILE_NOT_FOUND,
        message="Configuration file not found",
        details={"file_path": "/path/to/config.yaml"},
        cause=e
    )
```

#### Pattern 2: Validation Framework Errors
**When to Use:** Protocol validation, input validation, configuration errors
**Location:** `src/omnibase_core/validation/exceptions.py`

```python
from omnibase_core.validation.exceptions import (
    ConfigurationError,
    InputValidationError,
    FileProcessingError
)

# Example usage
def validate_path(path: str) -> None:
    if not path:
        raise InputValidationError("Path cannot be empty")

    if ".." in path:
        raise PathTraversalError(f"Path traversal detected: {path}")

def process_config_file(file_path: str) -> dict:
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise FileProcessingError(
            message="Configuration file not found",
            file_path=file_path,
            original_exception=e
        )
```

#### Pattern 3: Pydantic Validation
**When to Use:** Model validation, data structure validation
**Built-in to Pydantic models**

```python
from pydantic import BaseModel, ValidationError

class MyModel(BaseModel):
    value: int
    name: str

# Validation happens automatically
try:
    model = MyModel(value="not_an_int", name="test")
except ValidationError as e:
    # Handle validation error
    print(f"Validation failed: {e}")
```

#### Pattern 4: Custom RecursionError Protection
**When to Use:** Deep nested structure processing
**Location:** `src/omnibase_core/models/core/model_schema_value.py`

```python
# Built into ModelSchemaValueFactory
def from_value(cls, value: Any, _depth: int = 0) -> ModelSchemaValue:
    if _depth > cls._MAX_RECURSION_DEPTH:
        raise RecursionError(
            f"Maximum recursion depth ({cls._MAX_RECURSION_DEPTH}) exceeded"
        )
```

## Best Practices

### 1. Error Code Usage

- **Always use error codes** for OnexError instances
- **Use structured error codes** following the pattern: `ONEX_COMPONENT_###_DESCRIPTION`
- **Include context** in the details dictionary

### 2. Error Message Guidelines

- **Be specific and actionable**
- **Include relevant context** (file paths, operation details)
- **Avoid exposing sensitive information**
- **Use consistent terminology**

### 3. Error Chaining

```python
# Good: Preserve original exception
try:
    dangerous_operation()
except SomeException as e:
    raise OnexError(
        code=CoreErrorCode.OPERATION_FAILED,
        message="Operation failed during processing",
        cause=e  # Preserve original exception
    )

# Good: Chain validation framework errors
try:
    process_file(path)
except FileNotFoundError as e:
    raise FileProcessingError(
        message="Failed to process configuration",
        file_path=path,
        original_exception=e
    )
```

### 4. Error Recovery Patterns

```python
def robust_operation(retries: int = 3) -> Any:
    """Example of error recovery with retries."""
    last_error = None

    for attempt in range(retries):
        try:
            return risky_operation()
        except OnexError as e:
            last_error = e
            if attempt < retries - 1:
                # Log and retry
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                continue

    # All retries exhausted
    raise OnexError(
        code=CoreErrorCode.OPERATION_FAILED,
        message=f"Operation failed after {retries} attempts",
        details={"last_error": str(last_error)},
        cause=last_error
    )
```

## Decision Matrix

Use this matrix to choose the appropriate error handling pattern:

| Scenario | Pattern | Exception Type | Notes |
|----------|---------|----------------|-------|
| Core service errors | OnexError | OnexError | Use with error codes |
| Input validation | Validation Framework | InputValidationError | Security-focused |
| File operations | Validation Framework | FileProcessingError | Include file context |
| Model validation | Pydantic | ValidationError | Automatic validation |
| Configuration errors | Validation Framework | ConfigurationError | Fail-fast behavior |
| Deep recursion | Custom Protection | RecursionError | Built into factories |
| Protocol parsing | Validation Framework | ProtocolParsingError | AST/syntax errors |

## Error Serialization

### OnexError Serialization
```python
error = OnexError(
    code=CoreErrorCode.VALIDATION_FAILED,
    message="Data validation failed",
    details={"field": "username", "value": "invalid"}
)

# Serialize to dictionary
error_dict = error.to_dict()
# Output: {
#     "code": "ONEX_CORE_001_VALIDATION_FAILED",
#     "message": "Data validation failed",
#     "details": {"field": "username", "value": "invalid"}
# }
```

### ModelOnexError for API Responses
```python
from omnibase_core.models.core.model_onex_error import ModelOnexError

# Create structured error for API responses
api_error = ModelOnexError(
    message="File not found: config.yaml",
    error_code=EnumErrorCode.ONEX_CORE_011_FILE_NOT_FOUND,
    status=EnumOnexStatus.ERROR,
    context=error_context
)

# Serialize for JSON API response
response_data = api_error.model_dump()
```

## Testing Error Conditions

```python
import pytest
from omnibase_core.exceptions.base_onex_error import OnexError
from omnibase_core.validation.exceptions import InputValidationError

def test_error_handling():
    """Example of testing error conditions."""

    # Test OnexError raising
    with pytest.raises(OnexError) as exc_info:
        risky_operation_that_fails()

    assert exc_info.value.code == CoreErrorCode.EXPECTED_ERROR
    assert "expected message" in str(exc_info.value)

    # Test validation error
    with pytest.raises(InputValidationError):
        validate_input("")  # Empty input should fail

def test_error_serialization():
    """Test error serialization."""
    error = OnexError(
        code=CoreErrorCode.TEST_ERROR,
        message="Test message",
        details={"key": "value"}
    )

    serialized = error.to_dict()
    assert serialized["code"] == CoreErrorCode.TEST_ERROR.value
    assert serialized["message"] == "Test message"
    assert serialized["details"]["key"] == "value"
```

## Migration Notes

When migrating existing code:

1. **Replace generic exceptions** with specific ONEX exception types
2. **Add error codes** to all OnexError instances
3. **Include context** in error details
4. **Preserve error chains** using the `cause` parameter
5. **Update tests** to verify specific exception types and messages

## Performance Considerations

- **Error creation is expensive** - don't use exceptions for control flow
- **Error serialization** can be costly for complex details objects
- **Recursion protection** adds overhead but prevents stack overflow
- **Use appropriate error granularity** - not every condition needs a custom exception

## Security Considerations

- **Never expose sensitive data** in error messages
- **Validate all user inputs** before processing
- **Use PathTraversalError** for file path validation
- **Sanitize error details** before logging or returning to clients
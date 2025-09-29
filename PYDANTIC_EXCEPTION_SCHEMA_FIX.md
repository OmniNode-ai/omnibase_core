# Pydantic Exception Schema Generation Fix

## Problem

Pydantic cannot generate JSON schemas for raw `Exception` types, causing this error:

```
pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <class 'Exception'>
```

This occurs when you have BaseModel fields typed as `Exception` or `Exception | None`.

## ❌ Problematic Code

```python
from pydantic import BaseModel, Field
from typing import Optional

class ProblematicModel(BaseModel):
    """This will cause schema generation errors."""

    success: bool
    # ❌ This causes the error:
    error: Exception | None = Field(None, description="Error if any")

# This will fail:
schema = ProblematicModel.model_json_schema()  # ❌ PydanticSchemaGenerationError
```

## ✅ Solutions

### Solution 1: Field Serializers (Recommended for existing models)

Keep Exception fields but add proper serialization:

```python
from pydantic import BaseModel, Field, field_serializer, field_validator, ConfigDict
from typing import Optional, Any, Dict

class ModelWithSerializedExceptions(BaseModel):
    """Model that handles Exception fields with custom serialization."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Required for Exception fields
        validate_assignment=False,     # Avoid schema generation during assignment
        extra='ignore'
    )

    success: bool = Field(..., description="Operation success status")
    error: Optional[Exception] = Field(None, description="Error exception if any")

    @field_serializer('error', when_used='json')
    def serialize_error(self, value: Optional[Exception]) -> Optional[Dict[str, str]]:
        """Serialize Exception to JSON-safe dictionary."""
        if value is None:
            return None
        return {
            'type': type(value).__name__,
            'message': str(value),
            'module': type(value).__module__,
        }

    @field_validator('error', mode='before')
    @classmethod
    def validate_error(cls, value: Any) -> Optional[Exception]:
        """Validate and convert error field."""
        if value is None:
            return None
        if isinstance(value, Exception):
            return value
        if isinstance(value, dict):
            error_type = value.get('type', 'Exception')
            message = value.get('message', '')
            return Exception(f"{error_type}: {message}")
        if isinstance(value, str):
            return Exception(value)
        return Exception(str(value))
```

Usage:
```python
# Create with Exception
model = ModelWithSerializedExceptions(success=False, error=ValueError("Invalid input"))

# JSON serialization works
json_str = model.model_dump_json()
# Output: {"success": false, "error": {"type": "ValueError", "message": "Invalid input", "module": "builtins"}}

# Deserialization works
recreated = ModelWithSerializedExceptions.model_validate_json(json_str)
```

### Solution 2: Structured Error Models (Best for new code)

Replace Exception fields with structured error models:

```python
from pydantic import BaseModel, Field
from typing import Optional
import traceback as tb

class ModelErrorInfo(BaseModel):
    """Structured error information replacing raw Exception fields."""

    error_type: str = Field(..., description="Exception class name")
    message: str = Field(..., description="Error message")
    module: str = Field(..., description="Module where exception was defined")
    traceback_text: Optional[str] = Field(None, description="Exception traceback as string")

    @classmethod
    def from_exception(cls, exc: Exception) -> "ModelErrorInfo":
        """Create error info from Exception object."""
        tb_text = None
        if exc.__traceback__:
            tb_text = ''.join(tb.format_exception(type(exc), exc, exc.__traceback__))

        return cls(
            error_type=type(exc).__name__,
            message=str(exc),
            module=type(exc).__module__,
            traceback_text=tb_text
        )

    def to_exception(self) -> Exception:
        """Convert back to Exception object."""
        return Exception(f"{self.error_type}: {self.message}")


class ModelWithStructuredError(BaseModel):
    """Model using structured error instead of raw Exception."""

    success: bool = Field(..., description="Operation success status")
    error_info: Optional[ModelErrorInfo] = Field(None, description="Structured error information")

    @classmethod
    def from_exception(cls, success: bool, error: Optional[Exception] = None):
        """Create model from Exception object."""
        return cls(
            success=success,
            error_info=ModelErrorInfo.from_exception(error) if error else None
        )
```

Usage:
```python
# Create from Exception
model = ModelWithStructuredError.from_exception(
    success=False,
    error=RuntimeError("System error")
)

# JSON schema generation works perfectly
schema = ModelWithStructuredError.model_json_schema()

# Full JSON serialization/deserialization support
json_str = model.model_dump_json()
recreated = ModelWithStructuredError.model_validate_json(json_str)
```

### Solution 3: String-based Error Fields (Simplest)

Convert Exception fields to string fields with conversion methods:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ModelWithoutExceptionFields(BaseModel):
    """Model that avoids Exception fields entirely."""

    success: bool = Field(..., description="Operation success status")
    error_message: Optional[str] = Field(None, description="Error message if any")

    def record_error(self, error: Exception) -> None:
        """Record an error by converting it to a string."""
        self.error_message = f"{type(error).__name__}: {str(error)}"
        self.success = False

    def get_error_as_exception(self) -> Optional[Exception]:
        """Convert stored error message back to an Exception."""
        if not self.error_message:
            return None
        return Exception(self.error_message)
```

Usage:
```python
model = ModelWithoutExceptionFields(success=True)
model.record_error(ConnectionError("Database connection failed"))

# JSON schema generation works
schema = ModelWithoutExceptionFields.model_json_schema()

# Perfect JSON support
json_str = model.model_dump_json()  # No issues
```

## Migration Guide

### For Existing Models

1. **Identify problematic models** - Look for fields typed as `Exception` or `Exception | None`

2. **Choose your approach**:
   - **Quick fix**: Use Solution 1 (Field Serializers) - minimal code changes
   - **Best practice**: Use Solution 2 (Structured Errors) - better type safety and documentation
   - **Simple**: Use Solution 3 (String fields) - easiest to understand

3. **Update imports**:
   ```python
   from pydantic_exception_fix import ModelWithSerializedExceptions
   # or
   from pydantic_exception_fix import ModelWithStructuredError, ModelErrorInfo
   ```

### Example Migration

**Before (problematic)**:
```python
class RetryExecution(BaseModel):
    current_attempt: int
    last_error: Exception | None = None  # ❌ Causes schema error

    def record_attempt(self, error: Exception | None = None):
        self.last_error = error
```

**After (fixed with Solution 3)**:
```python
class RetryExecution(BaseModel):
    current_attempt: int
    last_error_message: str | None = None  # ✅ Works perfectly

    def record_attempt(self, error: Exception | None = None):
        if error:
            self.last_error_message = f"{type(error).__name__}: {str(error)}"

    def get_last_error(self) -> Exception | None:
        """Convert back to Exception if needed."""
        if not self.last_error_message:
            return None
        return Exception(self.last_error_message)
```

## Testing Your Fix

Create a test to verify your fix works:

```python
def test_exception_field_fix():
    """Test that Exception field handling works correctly."""

    # Test model creation
    model = YourFixedModel(success=False)
    model.record_error(ValueError("Test error"))

    # Test JSON schema generation (this should not fail)
    schema = YourFixedModel.model_json_schema()
    assert 'properties' in schema

    # Test JSON serialization/deserialization
    json_str = model.model_dump_json()
    recreated = YourFixedModel.model_validate_json(json_str)

    print("✅ Exception field fix working correctly!")

if __name__ == "__main__":
    test_exception_field_fix()
```

## Files Provided

- `pydantic_exception_fix.py` - Complete solutions with working implementations
- `test_and_fix_models.py` - Tests and examples of how to apply fixes
- `fix_pydantic_exception_schema.py` - Comprehensive testing script

## Best Practices

1. **For new models**: Use Solution 2 (Structured Errors) for the best type safety and API documentation

2. **For existing models**: Use Solution 1 (Field Serializers) for minimal code changes

3. **For simple cases**: Use Solution 3 (String fields) when you don't need complex error handling

4. **Always test** that your fix works by trying to generate a JSON schema:
   ```python
   schema = YourModel.model_json_schema()  # This should not fail
   ```

5. **Add proper configuration**:
   ```python
   model_config = ConfigDict(
       arbitrary_types_allowed=True,  # If keeping Exception fields
       validate_assignment=False      # Avoid schema generation during assignment
   )
   ```

## Summary

The Pydantic Exception schema generation error occurs because Pydantic cannot create JSON schemas for raw Exception types. The solutions provided here give you three different approaches to handle Exception fields properly while maintaining full JSON schema generation and serialization support.

Choose the solution that best fits your use case and existing codebase architecture.

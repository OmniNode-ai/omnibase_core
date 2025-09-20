# Field Accessor Migration Guide

This guide shows how to migrate from custom dict-like interfaces to the unified `ModelFieldAccessor` pattern across CLI, Config, and Data domains.

## Overview

The `ModelFieldAccessor` pattern provides:
- **Unified API**: Single interface for field access across all domains
- **Dot Notation**: `get_field("metadata.custom_fields.key")` syntax
- **Type Safety**: Specialized accessors with type coercion
- **Backward Compatibility**: Existing methods continue to work
- **Enhanced Capabilities**: Nested field access and navigation

## Migration Patterns

### 1. CLI Output Data Migration

#### Before: ModelCliOutputData
```python
class ModelCliOutputData(BaseModel):
    results: dict[str, str | int | bool | float] = Field(default_factory=dict)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    def get_field_value(self, key: str, default=None) -> Any:
        """Get a field value from results or metadata."""
        if key in self.results:
            return self.results[key]
        if key in self.metadata:
            return self.metadata[key]
        return default

    def set_field_value(self, key: str, value: Any) -> None:
        """Set a field value in results."""
        self.results[key] = value
```

#### After: Using ModelResultAccessor
```python
from omnibase_core.models.core.model_field_accessor import ModelResultAccessor

class ModelCliOutputData(ModelResultAccessor):
    results: dict[str, str | int | bool | float] = Field(default_factory=dict)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    # Methods inherited from ModelResultAccessor:
    # - get_result_value(key, default) -> checks both results and metadata
    # - set_result_value(key, value) -> sets in results
    # - set_metadata_value(key, value) -> sets in metadata
    # - get_field(path, default) -> dot notation access
    # - set_field(path, value) -> dot notation setting
```

#### Usage Examples
```python
# Old usage (still works with new methods)
cli_data = ModelCliOutputData()
cli_data.set_result_value("exit_code", 0)  # Replaces set_field_value
exit_code = cli_data.get_result_value("exit_code", -1)  # Replaces get_field_value

# New dot notation capabilities
cli_data.set_field("results.execution_time", 150.5)
cli_data.set_field("metadata.timestamp", "2024-01-01T12:00:00")
cli_data.set_field("metadata.performance.memory_mb", 64.2)

execution_time = cli_data.get_field("results.execution_time")
memory_usage = cli_data.get_field("metadata.performance.memory_mb", 0.0)
```

### 2. Generic Metadata Migration

#### Before: ModelGenericMetadata
```python
class ModelGenericMetadata(BaseModel):
    custom_fields: dict[str, str | int | bool | float] | None = Field(default=None)

    def get_field(self, key: str, default: Any = None) -> Any:
        """Get a custom field value."""
        if self.custom_fields is None:
            return default
        return self.custom_fields.get(key, default)

    def set_field(self, key: str, value: Any) -> None:
        """Set a custom field value."""
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value

    def has_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        if self.custom_fields is None:
            return False
        return key in self.custom_fields

    def remove_field(self, key: str) -> bool:
        """Remove a custom field."""
        if self.custom_fields is None:
            return False
        if key in self.custom_fields:
            del self.custom_fields[key]
            return True
        return False
```

#### After: Using ModelCustomFieldsAccessor
```python
from omnibase_core.models.core.model_field_accessor import ModelCustomFieldsAccessor

class ModelGenericMetadata(ModelCustomFieldsAccessor):
    custom_fields: dict[str, str | int | bool | float] | None = Field(default=None)

    # Methods inherited from ModelCustomFieldsAccessor:
    # - get_custom_field(key, default) -> replaces get_field
    # - set_custom_field(key, value) -> replaces set_field
    # - has_custom_field(key) -> replaces has_field
    # - remove_custom_field(key) -> replaces remove_field
    # - get_field(path, default) -> dot notation access
    # - set_field(path, value) -> dot notation setting
```

#### Usage Examples
```python
# Old usage (backward compatible with new method names)
metadata = ModelGenericMetadata()
metadata.set_custom_field("version", "1.0.0")  # Replaces set_field
version = metadata.get_custom_field("version", "unknown")  # Replaces get_field
has_version = metadata.has_custom_field("version")  # Replaces has_field

# New dot notation capabilities
metadata.set_field("custom_fields.build.number", 42)
metadata.set_field("custom_fields.build.timestamp", "2024-01-01T12:00:00")
metadata.set_field("custom_fields.deployment.environment", "production")

build_number = metadata.get_field("custom_fields.build.number", 0)
environment = metadata.get_field("custom_fields.deployment.environment", "development")
```

### 3. Environment Properties Migration

#### Before: ModelEnvironmentProperties
```python
class ModelEnvironmentProperties(BaseModel):
    properties: dict[str, PropertyValue] = Field(default_factory=dict)

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value."""
        value = self.properties.get(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value."""
        value = self.properties.get(key, default)
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            return int(value)
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value."""
        value = self.properties.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        if isinstance(value, (int, float)):
            return bool(value)
        return default
```

#### After: Using ModelEnvironmentAccessor
```python
from omnibase_core.models.core.model_field_accessor import ModelEnvironmentAccessor

class ModelEnvironmentProperties(ModelEnvironmentAccessor):
    properties: dict[str, PropertyValue] = Field(default_factory=dict)

    # Methods inherited from ModelEnvironmentAccessor:
    # - get_string(path, default) -> type coercion to string
    # - get_int(path, default) -> type coercion to int
    # - get_bool(path, default) -> type coercion to bool
    # - get_float(path, default) -> type coercion to float
    # - get_list(path, default) -> type coercion to list
    # - get_field(path, default) -> raw value access
    # - set_field(path, value) -> value setting
```

#### Usage Examples
```python
# Old usage (now with dot notation paths)
env_props = ModelEnvironmentProperties()
env_props.set_field("properties.database_host", "localhost")
env_props.set_field("properties.database_port", "5432")
env_props.set_field("properties.debug_mode", "true")

# Same API with enhanced path support
host = env_props.get_string("properties.database_host", "unknown")
port = env_props.get_int("properties.database_port", 3306)
debug = env_props.get_bool("properties.debug_mode", False)

# New nested configuration capabilities
env_props.set_field("properties.database.host", "localhost")
env_props.set_field("properties.database.port", "5432")
env_props.set_field("properties.features.auth.enabled", "true")
env_props.set_field("properties.features.logging.level", "info")

# Access nested configurations with type coercion
db_host = env_props.get_string("properties.database.host")
auth_enabled = env_props.get_bool("properties.features.auth.enabled")
log_level = env_props.get_string("properties.features.logging.level", "warn")
```

## Advanced Usage Patterns

### 1. Mixed Accessor Types
```python
from omnibase_core.models.core.model_field_accessor import (
    ModelFieldAccessor,
    ModelEnvironmentAccessor,
    ModelResultAccessor
)

class ComplexModel(ModelEnvironmentAccessor, ModelResultAccessor):
    """Model that combines multiple accessor patterns."""

    properties: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

# Usage combines both accessor types
model = ComplexModel()
model.set_field("properties.config.timeout", "30")
model.set_result_value("success", True)

timeout = model.get_int("properties.config.timeout", 10)  # Environment accessor
success = model.get_result_value("success", False)  # Result accessor
```

### 2. Type-Safe Access
```python
from omnibase_core.models.core.model_field_accessor import ModelTypedAccessor

class TypeSafeModel(ModelTypedAccessor[str]):
    data: dict[str, Any] = Field(default_factory=dict)

model = TypeSafeModel()
model.set_field("data.message", "hello")
model.set_field("data.count", 42)

# Type-safe access
message = model.get_typed_field("data.message", str, "default")  # Returns "hello"
count_as_str = model.get_typed_field("data.count", str, "0")     # Returns "0" (default)
count_as_int = model.get_typed_field("data.count", int, 0)       # Returns 42
```

### 3. Custom Specializations
```python
class ApiResponseAccessor(ModelFieldAccessor):
    """Custom accessor for API response patterns."""

    def get_status_code(self) -> int:
        """Get HTTP status code."""
        return self.get_field("response.status_code", 500)

    def get_error_message(self) -> str:
        """Get error message if any."""
        return self.get_field("response.error.message", "Unknown error")

    def is_success(self) -> bool:
        """Check if response was successful."""
        status = self.get_status_code()
        return 200 <= status < 300

class ApiModel(ApiResponseAccessor):
    response: dict[str, Any] = Field(default_factory=dict)

# Usage
api = ApiModel()
api.set_field("response.status_code", 200)
api.set_field("response.data.users", [{"id": 1, "name": "John"}])

print(f"Success: {api.is_success()}")  # True
print(f"Status: {api.get_status_code()}")  # 200
users = api.get_field("response.data.users", [])
```

## Migration Checklist

### Step 1: Choose the Right Accessor
- **ModelResultAccessor**: For CLI output data, execution results
- **ModelCustomFieldsAccessor**: For metadata, custom fields
- **ModelEnvironmentAccessor**: For configuration, properties with type coercion
- **ModelFieldAccessor**: For general-purpose field access
- **ModelTypedAccessor**: For type-safe access patterns

### Step 2: Update Model Inheritance
```python
# Before
class MyModel(BaseModel):
    # custom field methods

# After
class MyModel(ModelResultAccessor):  # or appropriate accessor
    # methods now inherited
```

### Step 3: Update Method Calls
- `get_field_value()` → `get_result_value()` or `get_field()`
- `set_field_value()` → `set_result_value()` or `set_field()`
- `get_field()` → `get_custom_field()` or `get_field()`
- Add dot notation paths where beneficial

### Step 4: Test Migration
- Verify existing functionality still works
- Test new dot notation capabilities
- Confirm type coercion works as expected
- Validate nested field access

### Step 5: Enhance with New Features
- Use dot notation for nested configurations
- Leverage type coercion methods
- Add custom accessor methods for domain-specific patterns

## Benefits

1. **Consistency**: Unified field access API across all domains
2. **Power**: Dot notation enables complex nested field access
3. **Type Safety**: Built-in type coercion and validation
4. **Extensibility**: Easy to create domain-specific accessors
5. **Backward Compatibility**: Existing code continues to work
6. **Performance**: Efficient field navigation and caching
7. **Maintainability**: Single pattern to learn and maintain
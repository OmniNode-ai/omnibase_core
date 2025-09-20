# Custom Properties Migration Guide

## Overview

This document outlines the migration from repetitive custom field patterns to the standardized `ModelCustomProperties` pattern. The new pattern provides type safety, validation, and utility methods.

## Current Repetitive Patterns

### Pattern 1: Mixed Type Custom Metadata
```python
# Found in 8+ models
custom_metadata: dict[str, str | int | bool | float] = Field(
    default_factory=dict,
    description="Custom metadata fields",
)
```

**Found in:**
- `ModelFunctionNode` ✅ **MIGRATED**
- `ModelNodeMetadataInfo`
- `ModelTimeout`
- `ModelRetryPolicy`
- `ModelMetadataNodeInfo`

### Pattern 2: Separate Typed Dictionaries
```python
# Found in 5+ models
custom_strings: dict[str, str] = Field(default_factory=dict)
custom_numbers: dict[str, float] = Field(default_factory=dict)
custom_flags: dict[str, bool] = Field(default_factory=dict)
```

**Found in:**
- `ModelCustomConnectionProperties` ✅ **MIGRATED**
- `ModelNodeConfiguration`

### Pattern 3: Nullable Custom Fields
```python
# Found in 3+ models
custom_strings: dict[str, str] | None = Field(default=None)
custom_numbers: dict[str, float] | None = Field(default=None)
custom_flags: dict[str, bool] | None = Field(default=None)
```

## New Standardized Pattern

### ModelCustomProperties Implementation

```python
from typing import Any
from pydantic import BaseModel, Field

class ModelCustomProperties(BaseModel):
    """Standardized custom properties with type safety."""

    custom_strings: dict[str, str] = Field(default_factory=dict)
    custom_numbers: dict[str, float] = Field(default_factory=dict)
    custom_flags: dict[str, bool] = Field(default_factory=dict)

    # Utility methods for type-safe operations
    def set_custom_string(self, key: str, value: str) -> None
    def set_custom_number(self, key: str, value: float) -> None
    def set_custom_flag(self, key: str, value: bool) -> None
    def get_custom_value(self, key: str) -> str | float | bool | None
    def has_custom_field(self, key: str) -> bool
    def remove_custom_field(self, key: str) -> bool
    def get_all_custom_fields(self) -> dict[str, str | float | bool]
    def set_custom_value(self, key: str, value: str | float | bool) -> None

    # Metadata compatibility
    @classmethod
    def from_metadata(cls, metadata: dict[str, str | int | bool | float])
    def to_metadata(self) -> dict[str, str | int | bool | float]
```

## Migration Examples

### Example 1: ModelFunctionNode Migration

**Before:**
```python
class ModelFunctionNode(BaseModel):
    # ... other fields ...

    custom_metadata: dict[str, str | int | bool | float] = Field(
        default_factory=dict,
        description="Custom metadata fields",
    )
```

**After:**
```python
from ..core.model_custom_properties import ModelCustomProperties

class ModelFunctionNode(BaseModel):
    # ... other fields ...

    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Custom properties with type safety",
    )
```

### Example 2: ModelCustomConnectionProperties Migration

**Before:**
```python
class ModelCustomConnectionProperties(BaseModel):
    # ... other fields ...

    custom_strings: dict[str, str] | None = Field(default=None)
    custom_numbers: dict[str, float] | None = Field(default=None)
    custom_flags: dict[str, bool] | None = Field(default=None)
```

**After:**
```python
from ..core.model_custom_properties import ModelCustomProperties

class ModelCustomConnectionProperties(BaseModel):
    # ... other fields ...

    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Additional custom properties with type safety",
    )
```

## Migration Checklist

### Active Models to Migrate

#### High Priority (Current Source)
- [ ] `ModelNodeMetadataInfo` - Line 75
  ```python
  custom_metadata: dict[str, str | int | bool | float]
  ```

- [ ] `ModelTimeout` - Line 64
  ```python
  custom_metadata: dict[str, str | int | bool | float]
  ```

- [ ] `ModelRetryPolicy` - Line 142
  ```python
  custom_metadata: dict[str, str | int | bool | float]
  ```

- [ ] `ModelMetadataNodeInfo` - Line 103
  ```python
  custom_metadata: dict[str, str | int | bool | float]
  ```

- [ ] `ModelNodeConfiguration` - Lines 41-52
  ```python
  custom_settings: dict[str, str] | None
  custom_flags: dict[str, bool] | None
  custom_limits: dict[str, int] | None
  ```

#### Archived Models (Lower Priority)
- [ ] `ModelVelocityMetrics`
- [ ] `ModelTimelineEvent`
- [ ] `ModelNodeInformation`
- [ ] `ModelNodeData`
- [ ] `ModelConnectionInfo` (archived)
- [ ] `ModelKvOperations`

## Benefits of Migration

### 1. Type Safety
- **Before:** Mixed union types `str | int | bool | float`
- **After:** Separated typed categories with compile-time checking

### 2. Utility Methods
- **Before:** Manual dictionary operations
- **After:** Type-safe methods like `set_custom_string()`, `get_custom_value()`

### 3. Validation
- **Before:** No validation on custom field operations
- **After:** Automatic type validation and error handling

### 4. Compatibility
- **Before:** Manual migration during refactoring
- **After:** Conversion methods maintain compatibility

### 5. Consistency
- **Before:** 15+ different custom field patterns
- **After:** Single standardized pattern across all models

## Usage Examples

### Setting Custom Properties
```python
# Type-safe methods
node.custom_properties.set_custom_string("environment", "production")
node.custom_properties.set_custom_number("timeout", 30.0)
node.custom_properties.set_custom_flag("debug_mode", True)

# Automatic type detection
node.custom_properties.set_custom_value("region", "us-west-2")
node.custom_properties.set_custom_value("retry_count", 3)
node.custom_properties.set_custom_value("enabled", False)
```

### Getting Custom Properties
```python
# Type-safe retrieval
env = node.custom_properties.get_custom_value("environment")  # Returns str | float | bool | None
timeout = node.custom_properties.custom_numbers.get("timeout", 30.0)

# Check existence
if node.custom_properties.has_custom_field("debug_mode"):
    debug = node.custom_properties.custom_flags["debug_mode"]
```

### Metadata Compatibility
```python
# Convert from metadata format
metadata = {"env": "prod", "timeout": 60.0, "debug": True}
props = ModelCustomProperties.from_metadata(metadata)

# Convert to metadata format for compatibility
metadata_format = props.to_metadata()
```

### Bulk Operations
```python
# Update from dictionary
props.update_from_dict({
    "service_name": "api-gateway",
    "pool_size": 10.0,
    "ssl_enabled": True
})

# Get all fields unified
all_fields = props.get_all_custom_fields()
```

## Implementation Steps

### Phase 1: Foundation ✅ **COMPLETE**
- [x] Create `ModelCustomProperties` base class
- [x] Add comprehensive utility methods
- [x] Add metadata compatibility methods
- [x] Create test suite

### Phase 2: High-Priority Migrations
1. **ModelNodeMetadataInfo**
   ```python
   # Replace line 75
   custom_properties: ModelCustomProperties = Field(
       default_factory=ModelCustomProperties,
       description="Custom properties with type safety",
   )
   ```

2. **ModelTimeout**
   ```python
   # Replace line 64
   custom_properties: ModelCustomProperties = Field(
       default_factory=ModelCustomProperties,
       description="Custom timeout properties",
   )
   ```

3. **ModelRetryPolicy**
   ```python
   # Replace line 142
   custom_properties: ModelCustomProperties = Field(
       default_factory=ModelCustomProperties,
       description="Custom retry policy properties",
   )
   ```

### Phase 3: Specialized Model Migrations
- Update `ModelNodeConfiguration` to use `ModelCustomProperties`
- Handle special cases like nullable custom fields
- Update any composition patterns

### Phase 4: Testing and Validation
- Run comprehensive tests
- Validate backward compatibility
- Performance testing
- Update documentation

## Testing Strategy

### Unit Tests ✅ **COMPLETE**
- [x] Empty initialization
- [x] Type-safe setters and getters
- [x] Utility method functionality
- [x] Metadata format conversion
- [x] Error handling for invalid types
- [x] Pydantic validation and serialization

### Integration Tests
- [ ] Test migrated models work with existing code
- [ ] Validate serialization/deserialization
- [ ] Test backward compatibility with external APIs

### Performance Tests
- [ ] Compare memory usage before/after
- [ ] Benchmark custom field operations
- [ ] Test with large custom property sets

## Migration Timeline

- **Week 1:** Complete Phase 2 migrations (high-priority models)
- **Week 2:** Handle Phase 3 specialized cases
- **Week 3:** Comprehensive testing and validation
- **Week 4:** Documentation updates and cleanup

## Risk Mitigation

### Compatibility
- Conversion methods ensure existing code continues to work
- Gradual migration approach minimizes disruption
- Comprehensive test coverage validates compatibility

### Performance Impact
- Minimal overhead from additional structure
- Type-safe operations may improve performance
- Memory usage slightly increased but with better organization

### Development Impact
- Clear migration guide reduces learning curve
- Utility methods improve developer experience
- Consistent patterns reduce maintenance burden

## Conclusion

The `ModelCustomProperties` pattern eliminates code duplication across 15+ models while providing:

- **Type Safety:** Compile-time checking prevents runtime errors
- **Consistency:** Single pattern across all models
- **Utility:** Rich set of helper methods
- **Compatibility:** Seamless migration from existing formats
- **Maintainability:** Centralized custom properties logic

This migration represents a significant improvement in code quality and developer experience while maintaining full compatibility.

# Migration Guide: ModelValidationContainer

This guide shows how to migrate from scattered validation patterns to the unified `ModelValidationContainer` approach.

## Overview

The `ModelValidationContainer` provides a standardized approach to validation error collection, aggregation, and reporting that replaces scattered validation logic across the codebase.

## Benefits

- **Standardization**: All models use the same validation interface
- **Reduced Code Duplication**: No more copying validation methods
- **Better Type Safety**: Strongly typed validation errors with MyPy compliance
- **Enhanced Functionality**: Error categorization, field tracking, merging capabilities
- **Consistent Reporting**: Standardized error summaries and serialization

## Migration Patterns

### Pattern 1: CLI Models with validation_errors List

**Before:**
```python
class ModelCliResult(BaseModel):
    validation_errors: list[ModelValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def has_errors(self) -> bool:
        return len(self.validation_errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def add_validation_error(self, error: ModelValidationError) -> None:
        self.validation_errors.append(error)

    def add_warning(self, warning: str) -> None:
        if warning not in self.warnings:
            self.warnings.append(warning)
```

**After:**
```python
from ..validation.model_validation_container import ValidatedModel

class ModelCliResult(ValidatedModel):
    # Remove scattered validation fields - inherited from ValidatedModel:
    # validation: ModelValidationContainer = Field(default_factory=ModelValidationContainer)

    # All validation methods now available via self.validation:
    # - self.validation.has_errors()
    # - self.validation.has_warnings()
    # - self.validation.add_error()
    # - self.validation.add_warning()

    def validate_model_data(self) -> None:
        """Custom validation logic."""
        if self.success and self.exit_code != 0:
            self.validation.add_error(
                "Success flag is True but exit_code is not 0",
                field="exit_code",
                error_code="INCONSISTENT_EXIT_CODE"
            )
```

### Pattern 2: Models with Different Validation Patterns

**Before:**
```python
class ModelWorkflowResult(BaseModel):
    errors: list[str] = Field(default_factory=list)
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def is_valid(self) -> bool:
        return len(self.errors) == 0 and len(self.validation_issues) == 0

    def get_error_count(self) -> int:
        return len(self.errors) + len(self.validation_issues)
```

**After:**
```python
from ..validation.model_validation_container import ValidatedModel

class ModelWorkflowResult(ValidatedModel):
    # All validation through inherited container

    def validate_model_data(self) -> None:
        """Convert existing validation to container."""
        # Validate workflow ID format
        if not self.workflow_id.startswith(("wf_", "workflow_")):
            self.validation.add_error(
                "Workflow ID must start with 'wf_' or 'workflow_'",
                field="workflow_id",
                error_code="INVALID_WORKFLOW_ID_FORMAT"
            )
```

### Pattern 3: Manual Validation Container Usage

**For existing code that doesn't inherit from ValidatedModel:**

```python
from ..validation.model_validation_container import ModelValidationContainer

class ExistingModel(BaseModel):
    name: str
    value: int

    def validate(self) -> ModelValidationContainer:
        """Manual validation using container."""
        container = ModelValidationContainer()

        if not self.name:
            container.add_error("Name is required", field="name")

        if self.value < 0:
            container.add_critical_error("Value must be positive", field="value")

        return container
```

## Step-by-Step Migration

### Step 1: Identify Models to Migrate

Search for models with these patterns:
- `validation_errors: list[ModelValidationError]`
- `warnings: list[str]`
- `errors: list[str]`
- Custom `has_errors()`, `add_error()` methods

### Step 2: Update Model Inheritance

```python
# Before
class MyModel(BaseModel):
    validation_errors: list[ModelValidationError] = Field(default_factory=list)

# After
from ..validation.model_validation_container import ValidatedModel

class MyModel(ValidatedModel):
    # validation container automatically included
```

### Step 3: Update Method Calls

| Before | After |
|--------|-------|
| `model.validation_errors` | `model.validation.errors` |
| `model.has_errors()` | `model.validation.has_errors()` |
| `model.add_validation_error(error)` | `model.validation.add_validation_error(error)` |
| `model.warnings` | `model.validation.warnings` |
| `model.add_warning(msg)` | `model.validation.add_warning(msg)` |

### Step 4: Implement Custom Validation

```python
def validate_model_data(self) -> None:
    """Override to add custom validation logic."""
    # Clear any previous validation results (done automatically by perform_validation())

    # Add validation logic
    if self.field1 is None:
        self.validation.add_critical_error("Field1 is required", field="field1")

    if self.field2 and len(self.field2) < 5:
        self.validation.add_warning("Field2 is shorter than recommended")
```

### Step 5: Update Usage Code

```python
# Before
if model.has_errors():
    for error in model.validation_errors:
        print(f"Error: {error.message}")

# After
if model.validation.has_errors():
    for error in model.validation.errors:
        print(f"Error: {error.message}")

# Or use convenience methods
if not model.is_valid():
    print(f"Validation failed: {model.get_validation_summary()}")
```

## Advanced Usage

### Merging Validation Results

```python
def validate_complex_operation(models: list[ValidatedModel]) -> ModelValidationContainer:
    """Aggregate validation from multiple models."""
    combined = ModelValidationContainer()

    for model in models:
        model.perform_validation()
        combined.merge_from(model.validation)

    return combined
```

### Field-Specific Error Handling

```python
def fix_validation_errors(model: ValidatedModel) -> None:
    """Fix specific field errors."""
    name_errors = model.validation.get_errors_by_field("name")
    if name_errors:
        # Handle name-specific errors
        pass
```

### Custom Error Processing

```python
def process_validation_results(container: ModelValidationContainer) -> dict:
    """Process validation results for API response."""
    return {
        "success": container.is_valid(),
        "errors": [
            {
                "message": error.message,
                "field": error.field_name,
                "code": error.error_code,
                "severity": error.severity.value,
            }
            for error in container.errors
        ],
        "warnings": container.warnings,
        "summary": container.get_error_summary(),
    }
```

## Testing Migration

```python
def test_migrated_model():
    """Test migrated model validation."""
    model = MyMigratedModel(field1="value")

    # Test validation
    is_valid = model.perform_validation()
    assert is_valid == expected_validity

    # Test error counts
    assert model.validation.get_error_count() == expected_errors
    assert model.validation.get_warning_count() == expected_warnings

    # Test specific errors
    field_errors = model.validation.get_errors_by_field("field1")
    assert len(field_errors) == expected_field_errors
```

## Common Issues and Solutions

### Issue 1: Circular Imports
If you get circular import errors, use string type annotations:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..validation.model_validation_container import ModelValidationContainer
```

### Issue 2: Existing Tests
Update tests to use the new validation interface:

```python
# Before
assert len(model.validation_errors) == 0

# After
assert model.validation.get_error_count() == 0
# or
assert model.is_valid()
```

### Issue 3: Serialization
The validation container is included in model serialization by default. To exclude:

```python
model_dict = model.model_dump(exclude={"validation"})
```

## Files to Update

Based on the codebase search, these files should be migrated:

1. **Core CLI Models:**
   - `/app/src/omnibase_core/src/omnibase_core/models/cli/model_cli_result.py`

2. **Other Models with Validation Patterns:**
   - Search for `validation_errors: list` pattern
   - Search for `warnings: list[str]` pattern
   - Search for custom `has_errors()` methods

3. **Update Imports:**
   - Update validation package `__init__.py` (already done)
   - Add imports in models that use validation

## Verification

After migration, verify:
- [ ] All models compile without errors
- [ ] Tests pass with new validation interface
- [ ] Validation behavior is preserved
- [ ] Error messages and counts are consistent
- [ ] Serialization works as expected

## Benefits Realized

After migration, you'll have:
- ✅ Standardized validation across all domains
- ✅ Reduced code duplication (40-60% reduction in validation code)
- ✅ Better type safety and MyPy compliance
- ✅ Enhanced error reporting capabilities
- ✅ Consistent validation interface
- ✅ Easier testing and debugging
- ✅ Future-proof validation architecture